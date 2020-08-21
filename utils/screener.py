import ccxt
import json


class Screener:
    def __init__(self, stake_currency, bot_data):

        self.stake_currency = stake_currency

        exchange_class = getattr(ccxt, 'binance')
        self.exchange = exchange_class({
            'apiKey': bot_data['exchange_key'],
            'secret': bot_data['exchange_secret'],
            'timeout': 30000,
            'enableRateLimit': True,
        })

    def get_pairs(self):
        # response = self.exchange.fetchTradingFees()
        response = self.exchange.fetchTickers()
        # response = self.binance_client.get_trade_fee()

        pairs = []
        for pair in response.keys():
            if self.stake_currency in pair:
                print(pair)
                pairs.append(pair)

        print(len(pairs))


if __name__ == '__main__':
    with open('../bots_config.json') as bots_config:
        data = json.load(bots_config)

    screener = Screener('USDT', data['bots_data'][6])
    screener.get_pairs()