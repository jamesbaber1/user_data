import time
import json
import math
import ccxt
import logging
import paramiko
import requests
import rapidjson
import datetime
import telegram
import threading

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('paramiko').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('ccxt').setLevel(logging.WARNING)


class Bot:
    def __init__(self, bot_data, bot_alert_data):
        self.name = bot_data['name']
        self.dry_run = bot_data['dry_run']
        self.full_reset = bot_data['full_reset']
        self.initial_state = bot_data['initial_state']
        self.host_name = bot_data['host_name']
        self.user_name = bot_data['user_name']
        self.config_url = bot_data['config']
        self.config_file = bot_data["config"].rsplit("/", 1)[-1]
        self.config_values = self.get_config_values()
        self.strategy_url = bot_data['strategy']
        self.strategy_file = bot_data['strategy'].rsplit("/", 1)[-1]
        self.strategy_class = self.strategy_file.replace('.py', '')
        self.exchange_key = bot_data['exchange_key']
        self.exchange_secret = bot_data['exchange_secret']
        self.telegram_chat_id = bot_data['telegram_chat_id']
        self.telegram_token = bot_data['telegram_token']
        self.api_server_username = bot_data['api_server_username']
        self.api_server_password = bot_data['api_server_password']
        self.stake_currency = self.config_values['stake_currency']
        self.fiat_display_currency = self.config_values['fiat_display_currency']

        self.get_current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if bot_data.get('private_key'):
            self.private_key = paramiko.RSAKey.from_private_key_file(bot_data['private_key'])
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        exchange_class = getattr(ccxt, 'binance')
        self.exchange = exchange_class({
            'apiKey': self.exchange_key,
            'secret': self.exchange_secret,
            'timeout': 30000,
            'enableRateLimit': True,
        })

        self.alert_bot = telegram.Bot(token=bot_alert_data['telegram_token'])
        self.alert_bot_telegram_chat_id = bot_alert_data['telegram_chat_id']

    def get_config_values(self):
        # get the config text from the config url
        response = requests.get(self.config_url)

        # load in the config as json
        return rapidjson.loads(
            response.text,
            parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
        )

    def bash_command(self, command):
        self.open_connection()
        bash_input, terminal_output, error = self.client.exec_command(command)

        error_message = error.read().decode("utf-8")
        output = terminal_output.read().decode("utf-8").split('\n')

        self.close_connection()

        if error_message:
            return error_message

        return output

    def run_detached_command(self, command):
        self.open_connection()

        # run the commands in a separate detached channel
        transport = self.client.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)
        self.close_connection()

    def open_connection(self):
        self.client.connect(
            hostname=self.host_name,
            username=self.user_name,
            pkey=self.private_key
        )

    def close_connection(self):
        self.client.close()

    def reboot_machine(self):
        logging.debug(f'rebooting the {self.name} machine...')
        self.bash_command('sudo reboot')

    def check_connection(self, fail_count=1):
        try:
            if fail_count < 5:
                # wait 3 seconds before attempting to connect to the remote machine
                time.sleep(3)

                # try to run a command to test the connection
                logging.debug(f'attempt {fail_count} to connect to the {self.name} machine...')
                self.bash_command('echo "connected"')
            else:
                logging.error(f'no ssh connection to the {self.name} machine could be made!')

        # if a connection error is thrown, try again and increase the fail count
        except Exception:
            self.check_connection(fail_count + 1)

    def ping_bot(self, fail_count=1):
        try:
            logging.debug(f'attempt {fail_count} to ping {self.name} api server...')
            if fail_count < 10:
                # wait 1 second before pinging the server
                time.sleep(1)
                response = requests.get(f'http://{self.host_name}:8080/api/v1/ping')
                return response
            else:
                logging.error(f'failed to ping {self.name} api server! {self.name} is not running!')
                return None

        except requests.exceptions.ConnectionError:
            self.ping_bot(fail_count + 1)

    def stop_bot(self, fail_count=0):
        response = self.api_post('stop')
        if response:
            status = response['status']
            if status != 'already stopped' and fail_count < 5:
                logging.debug(f'{self.name} is {status}')
                time.sleep(5)
                self.stop_bot(fail_count + 1)

    def start_bot(self):
        # run the commands in a separate detached channel
        logging.debug(f'starting {self.name}...')
        self.run_detached_command('\n'.join([
            f'cd freqtrade/',
            f'source .env/bin/activate',
            f'freqtrade trade -c {self.config_file} -s {self.strategy_class}'
        ]))

        # ping the api to see if the bot is running
        self.ping_bot()
        logging.info(f'{self.name} is running!')

    def install_strategy(self):
        # download the latest strategy file
        logging.debug(f'{self.name} downloading strategy file {self.strategy_url}')
        self.bash_command('\n'.join([
            f'cd freqtrade/user_data/strategies/',
            f'wget {self.strategy_url} -O {self.strategy_file}'
        ]))

    def install_config(self):
        # override these config key values using the bot data
        logging.debug(f'{self.name} populating bot_data into {self.config_file}')
        self.config_values['dry_run'] = self.dry_run
        self.config_values['initial_state'] = self.initial_state
        self.config_values['exchange']['key'] = self.exchange_key
        self.config_values['exchange']['secret'] = self.exchange_secret
        self.config_values['telegram']['chat_id'] = self.telegram_chat_id
        self.config_values['telegram']['token'] = self.telegram_token
        self.config_values['api_server']['username'] = self.api_server_username
        self.config_values['api_server']['password'] = self.api_server_password

        logging.debug(f'{self.name} downloading config file {self.config_url}')
        self.bash_command('\n'.join([
            f"config_data=$'{rapidjson.dumps(self.config_values, indent=2)}'",
            f'config_file=/home/ubuntu/freqtrade/{self.config_file}',
            f'echo "$config_data" > "$config_file"'
        ]))

    def remove_databases(self):
        logging.debug(f'{self.name} removing databases...')

        if self.dry_run:
            remove_database_command = 'rm tradesv3.dryrun.sqlite'
        else:
            remove_database_command = 'rm tradesv3.sqlite'

        self.bash_command('\n'.join([
            'cd freqtrade/',
            remove_database_command
        ]))

    def truncate(self, number, digits):
        stepper = 10.0 ** digits
        return math.trunc(stepper * number) / stepper

    def api_post(self, command):
        try:
            response = requests.post(
                f'http://{self.host_name}:8080/api/v1/{command}',
                auth=(self.api_server_username, self.api_server_password),
                timeout=5
            )
            return json.loads(response.text)
        except Exception as error:
            self.report_error(str(error))
            return []

    def api_get(self, command):
        try:
            response = requests.get(
                f'http://{self.host_name}:8080/api/v1/{command}',
                auth=(self.api_server_username, self.api_server_password),
                timeout=5
            )
            return json.loads(response.text)
        except Exception as error:
            self.report_error(str(error))
            return []

    def convert_coin_dust(self):
        # get the coins that are below the dust amount
        dust_coins = self.get_coin_balances(only_dust=True)
        # remove BNB from the list of coins to be converted
        if 'BNB' in dust_coins:
            dust_coins.pop('BNB')

        if dust_coins:
            logging.debug(f"{self.name} is cleaning up coin dust...")

            # convert all the dust coins to BNB
            try:
                self.exchange.sapiPostAssetDust(
                    params={
                        'asset': list(dust_coins.keys())
                    }
                )
            except Exception as error:
                logging.error(error)

    def sort_balances(self, balances):
        sorted_balances = []

        for balance in balances:
            sorted_balances.append([balance["currency"], balance['balance']])
        sorted_balances.sort(key=lambda x: x[1], reverse=True)

        return sorted_balances

    def cancel_all_orders(self):
        # get all open orders
        orders = self.exchange.privateGetOpenOrders()
        if orders:
            logging.debug(f'{self.name} is canceling all orders...')

            # get the full ticker names with slashes from symbols without slashes
            symbols = {}
            tickers = bot.exchange.fetchTickers()
            for ticker in tickers.keys():
                symbols[ticker.replace('/', '')] = ticker

            # cancel each open order
            for order in orders:
                logging.debug(f"{self.name} canceling {order['side']} order for {order['symbol']}...")
                self.exchange.cancel_order(
                    order['orderId'],
                    symbols[order['symbol']],
                    params={
                        'clientOrderId': order['clientOrderId']
                    })

    def get_prices(self):
        prices = self.exchange.v3GetTickerPrice()
        return {p['symbol']: float(p['price']) for p in prices}

    def get_balances(self):
        account = self.exchange.fetchBalance(params={'type': 'SPOT'})['info']
        return {b['asset']: float(b['free']) for b in account['balances']}

    def get_total_account_balance(self):
        prices = self.get_prices()
        balances = self.get_balances()

        total = 0

        for ticker, amount in balances.items():
            price = prices.get(f'{ticker}{self.stake_currency}') or prices.get(f'{self.stake_currency}{ticker}')

            if price and amount > 0:
                total = total + price

        # get the price of the stake currency against the price of the fiat display currency
        fiat_price = prices.get('USDT/USD')
        #     f'{self.fiat_display_currency}{self.stake_currency}'
        # ) or prices.get(
        #     f'{self.stake_currency}{self.fiat_display_currency}'
        # )

        print(fiat_price)

        total = (total + balances[self.stake_currency]) * fiat_price

        return total

    def get_coin_balances(self, only_dust=False, only_non_dust=False):
        dust_coins = {}
        non_dust_coins = {}

        prices = self.get_prices()
        balances = self.get_balances()

        # calculate the dust amount relative to the BTC
        if self.stake_currency != 'BTC':
            stake_currency_price = prices.get(f'{self.stake_currency}BTC') or prices.get(f'BTC{self.stake_currency}')
            dust = stake_currency_price * 0.001
        else:
            dust = 0.001

        for ticker, amount in balances.items():
            price = prices.get(f'{ticker}{self.stake_currency}')
            if not price:
                price = prices.get(f'{self.stake_currency}{ticker}')

            if price:
                value = amount * price

                if value <= dust and value > 0:
                    dust_coins[ticker] = amount

                if value > dust:
                    non_dust_coins[ticker] = amount

        if only_dust:
            return dust_coins

        if only_non_dust:
            return non_dust_coins

        else:
            return dust_coins.update(non_dust_coins)

    def convert_all_coins_to_stake_coin(self):
        # convert all non dust coins to the stake coin
        non_dust_coins = self.get_coin_balances(only_non_dust=True)
        if non_dust_coins:
            logging.debug(f'{self.name} is converting all coins to {self.stake_currency}...')
            for ticker, amount in non_dust_coins.items():
                try:
                    self.exchange.create_market_sell_order(
                        symbol=f'{ticker}/{self.stake_currency}',
                        amount=self.truncate(amount, 4)
                    )
                    logging.debug(f"Selling {self.truncate(amount, 4)} of {ticker}/{self.stake_currency}")
                except Exception as error:
                    logging.error(error)

    def report_error(self, message):
        bot_error_message = f'{self.name} Error:\n{message}'

        self.alert_bot.send_message(
            chat_id=self.alert_bot_telegram_chat_id,
            text=bot_error_message
        )

    def update_bot(self):
        # check the connection
        self.check_connection()

        # stop the bot
        self.stop_bot()

        # if it is a full reset, delete the databases and sell all alt coins
        if self.full_reset:
            self.cancel_all_orders()
            self.convert_all_coins_to_stake_coin()
            self.convert_coin_dust()
            self.remove_databases()

        # reboot the remote machine
        self.reboot_machine()

        # check the connection again since we just rebooted
        self.check_connection()

        # install the config
        self.install_config()

        # install the strategy
        self.install_strategy()

        # start the bot
        self.start_bot()


if __name__ == "__main__":
    with open('../bots_config.json') as bots_config:
        data = json.load(bots_config)

    for bot_data in data['bots_data']:
        # instantiate a new bot connection
        bot = Bot(bot_data, data['bot_alerts'])

        if bot_data['update']:
            # update the bot on a separate thread
            update_bot_thread = threading.Thread(target=bot.update_bot)
            update_bot_thread.start()
