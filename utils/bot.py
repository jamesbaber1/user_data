import time
import json
import math
import logging
import paramiko
import requests
import rapidjson
import datetime
import telegram
import threading
from requests.exceptions import ConnectionError, Timeout, HTTPError, TooManyRedirects, ReadTimeout
from binance.client import Client
from binance.exceptions import BinanceAPIException

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('paramiko').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


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
        self.strategy_url = bot_data['strategy']
        self.strategy_file = bot_data['strategy'].rsplit("/", 1)[-1]
        self.strategy_class = self.strategy_file.replace('.py', '')
        self.exchange_key = bot_data['exchange_key']
        self.exchange_secret = bot_data['exchange_secret']
        self.telegram_chat_id = bot_data['telegram_chat_id']
        self.telegram_token = bot_data['telegram_token']
        self.api_server_username = bot_data['api_server_username']
        self.api_server_password = bot_data['api_server_password']

        self.get_current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        if bot_data.get('private_key'):
            self.private_key = paramiko.RSAKey.from_private_key_file(bot_data['private_key'])
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.binance_client = Client(self.exchange_key, self.exchange_secret)

        self.alert_bot = telegram.Bot(token=bot_alert_data['telegram_token'])
        self.alert_bot_telegram_chat_id = bot_alert_data['telegram_chat_id']

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
            self.check_connection(fail_count+1)

    def ping_bot(self, fail_count=1):
        try:
            logging.debug(f'attempt {fail_count} to ping {self.name} api server...')
            if fail_count < 10:
                # wait 1 second before pinging the server
                time.sleep(1)
                response = requests.get(f'http://{self.host_name}:8080/api/v1/ping')
                return json.loads(response.text)
            else:
                logging.error(f'failed to ping {self.name} api server! {self.name} is not running!')

        except requests.exceptions.ConnectionError:
            self.ping_bot(fail_count+1)

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
        logging.info(f'successfully started {self.name}!')

    def install_strategy(self):
        # download the latest strategy file
        logging.debug(f'{self.name} downloading strategy file {self.strategy_url}')
        self.bash_command('\n'.join([
            f'cd freqtrade/user_data/strategies/',
            f'wget {self.strategy_url} -O {self.strategy_file}'
        ]))

    def install_config(self):
        # get the config text from the config url
        logging.debug(f'{self.name} downloading config file {self.config_url}')
        response = requests.get(self.config_url)

        # load in the text as json
        config = rapidjson.loads(
            response.text,
            parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
        )

        # override these config key values using the bot data
        logging.debug(f'{self.name} populating bot_data into {self.config_file}')
        config['dry_run'] = self.dry_run
        config['initial_state'] = self.initial_state
        config['exchange']['key'] = self.exchange_key
        config['exchange']['secret'] = self.exchange_secret
        config['telegram']['chat_id'] = self.telegram_chat_id
        config['telegram']['token'] = self.telegram_token
        config['api_server']['username'] = self.api_server_username
        config['api_server']['password'] = self.api_server_password

        self.bash_command('\n'.join([
            f"config_data=$'{rapidjson.dumps(config, indent=2)}'",
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

    def sell_coin_dust(self, coins):
        # try to convert all the coin dust to BNB
        logging.debug(f'{self.name} is converting all coin dust to BNB...')
        for coin in coins:
            try:
                self.binance_client.transfer_dust(asset=coin)

            except BinanceAPIException as error:
                if error.code != -5002:
                    logging.error(error.message)

    def force_sell_all_coins(self):
        logging.debug(f'resetting coin balances for {self.name} by selling all alt coins...')
        account_balance = self.api_get('balance')

        coin_dust = set()

        # make a market orders to sell all coins except BTC and BNB
        for coin in account_balance['currencies']:
            if coin['currency'] not in ['BTC', 'BNB']:
                try:
                    logging.debug(f'{self.name} selling {self.truncate(coin["balance"], 8)} {coin["currency"]}...')

                    self.binance_client.create_order(
                        symbol=f"{coin['currency']}BTC",
                        side=Client.SIDE_SELL,
                        type=Client.ORDER_TYPE_MARKET,
                        quantity=self.truncate(coin['balance'], 8)
                    )

                # if the lot size is too small sell the remaining coin dust
                except BinanceAPIException as error:
                    if error.code == -1013:
                        coin_dust.add(coin['currency'])

                remaining_amount = self.binance_client.get_asset_balance(coin["currency"])
                if remaining_amount:
                    logging.debug(f'{self.name} has {remaining_amount["free"]} {coin["currency"]} remaining...')

        self.sell_coin_dust(list(coin_dust))

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
            # self.force_sell_all_coins()
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
    with open('bots_config.json') as bots_config:
        data = json.load(bots_config)

    for bot_data in data['bots_data']:
        # instantiate a new bot connection
        bot = Bot(bot_data, data['bot_alerts'])

        if bot_data['update']:
            # update the bot on a separate thread
            update_bot_thread = threading.Thread(target=bot.update_bot)
            update_bot_thread.start()