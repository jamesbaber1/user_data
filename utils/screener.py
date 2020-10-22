import ccxt
import os
import json
from datetime import datetime
from datetime import timedelta


class Screener:
    def __init__(self, bot_data, stake_currency, config, strategy, days, candle_time):


        exchange_class = getattr(ccxt, 'binance')
        self.exchange = exchange_class({
            'apiKey': bot_data['exchange_key'],
            'secret': bot_data['exchange_secret'],
            'timeout': 30000,
            'enableRateLimit': True,
        })

        self.stake_currency = stake_currency
        self.config = config
        self.strategy = strategy
        self.days = days
        self.candle_time = candle_time
        self.time_range = self.get_time_range()
        self.pairs = self.get_pairs()
        self.validate_coin_pairs()

    def get_time_range(self):
        time_range = datetime.today() - timedelta(days=self.days)
        return time_range.strftime('%Y%m%d')

    def get_pairs(self):
        pairs = []
        response = self.exchange.fetchTickers()

        for pair in response.keys():
            if self.stake_currency in pair:
                pairs.append(pair)

        return pairs

    def download_candles(self):
        # freqtrade.main(
        #     parameters=[
        #         'download-data',
        #         '--config', self.config,
        #         '--days', str(self.days),
        #         '-t', self.candle_time
        #     ],
        #     screener_whitelist=self.pairs
        # )
        pass

    def backtest(self):
        # freqtrade.main(
        #     parameters=[
        #         'backtesting',
        #         '--export', 'trades',
        #         '--config', self.config,
        #         '--strategy', self.strategy,
        #         f'--timerange={self.time_range}-'
        #     ],
        #     screener_whitelist=self.pairs
        # )
        pass

    def remove_bad_whitelist_pairs(self):
        # log_file_path = freqtrade.get_full_path(['freqtrade', 'user_data', 'logs', 'commands.log'])
        # print(log_file_path)
        # log_file = open(log_file_path, 'r')
        #
        # bad_pairs = []
        # for line in log_file:
        #     message = 'Please remove the following pairs:'
        #     if message in line:
        #         error_message = line.split(message)[-1].strip()
        #         bad_pairs = error_message.replace(' ', '').replace('[', '').replace(']', '').replace("'", '').split(',')
        #
        # self.pairs = [coin for coin in self.pairs if coin not in bad_pairs]

        pass

    def validate_coin_pairs(self):
        try:
            self.download_candles()
        except RuntimeError:
            self.remove_bad_whitelist_pairs()


if __name__ == '__main__':
    with open('../bots_config.json') as bots_config:
        data = json.load(bots_config)

    # get all the
    screener = Screener(
        bot_data=data['bots_data'][6],
        stake_currency='USDT',
        config='config_usdt_04.json',
        strategy='BB_Strategy02',
        days=30,
        candle_time='1d'
    )

    # screener.download_candles()
    # screener.backtest()

    pairs = screener.get_pairs()
    etfs = []

    for pair in pairs:
        if 'UP' in pair or 'DOWN' in pair:
            etfs.append(pair)
    import pprint
    pprint.pprint(etfs)

    # screener.download_candles(pairs=pairs, config=config, candles='30', candle_time='1d')
    # screener.backtest(config=config, strategy=strategy, time_range='20200721', pairs=pairs)