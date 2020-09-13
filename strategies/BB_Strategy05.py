# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import logging
from datetime import datetime
logger = logging.getLogger('freqtrade.worker')


class BB_Strategy05(IStrategy):
    """
    This is a strategy template to get you started.
    More information in https://github.com/freqtrade/freqtrade/blob/develop/docs/bot-optimization.md

    You can:
        :return: a Dataframe with all mandatory indicators for the strategies
    - Rename the class name (Do not forget to update class_name)
    - Add any methods you want to build your strategy
    - Add any lib you need to build your strategy

    You must keep:
    - the lib in the section "Do not remove these libs"
    - the prototype for the methods: minimal_roi, stoploss, populate_indicators, populate_buy_trend,
    populate_sell_trend, hyperopt_space, buy_strategy_generator
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 2

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 1.09767,
        "3178": 0.31206,
        "13523": 0.05282,
        "38158": 0
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.33

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Optimal ticker interval for the strategy.
    ticker_interval = '1m'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

    disable_dataframe_checks = True

    # Number of candles the strategy requires before producing valid signals
    # startup_candle_count: int = 10

    # Optional order type mapping.
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc'
    }

    plot_config = {
        # Main plot indicators (Moving averages, ...)
        'main_plot': {
            'bb_lowerband1': {'color': 'green'},
            'bb_middleband1': {'color': 'red'},
            'bb_upperband1': {'color': 'green'},
            # 'ma': {'color': 'blue'}
        }
    }

    def informative_pairs(self):

        # get access to all pairs available in whitelist.
        pairs = self.dp.current_whitelist()
        # Assign tf to each pair so they can be downloaded and cached for strategy.
        informative_pairs = [(pair, '1d') for pair in pairs]

        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        if not self.dp:
            # Don't do anything if DataProvider is not available.
            return dataframe

        inf_tf = '1d'
        # Get the informative pair
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=inf_tf)

        if self.dp:
            if self.dp.runmode.value in ('live', 'dry_run'):

                now = datetime.utcnow()
                time = pd.Timestamp(year=now.year, month=now.month, day=now.day, tz="GMT+0")

                ticker = self.dp.ticker(metadata['pair'])
                new_row = {
                    'date': time,
                    'open': informative['open'].values[-1],
                    'high': informative['high'].values[-1],
                    'low': informative['low'].values[-1],
                    'close': ticker['last'],
                    'volume': informative['volume'].values[-1]
                }
                informative = informative.append(new_row, ignore_index=True)

        # calculate the bollinger bands with 1d candles
        bollinger = qtpylib.bollinger_bands(informative['close'], window=3, stds=1)
        informative[f'bb_lowerband1'] = bollinger['lower']
        informative[f'bb_middleband1'] = bollinger['mid']
        informative[f'bb_upperband1'] = bollinger['upper']

        dataframe = informative

        # pd.set_option('display.max_columns', None)
        # pd.set_option('display.width', 300)
        # pd.get_option("display.max_colwidth")
        logger.info(f'-----Populate----Pair: {metadata["pair"]}-------------------')
        logger.info(f'\n\n{dataframe.to_markdown()}')
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                # (qtpylib.crossed_above(dataframe['close'], dataframe['bb_lowerband1_1d']))
                (dataframe['close'] < dataframe['bb_lowerband1'])  # &
                # (dataframe['volume'] > self.config['stake_amount'])
            ),
            'buy'] = 1

        logger.info(f'-----Buy----Pair: {metadata["pair"]}-------------------')
        logger.info(f'\n\n{dataframe.to_markdown()}')

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame populated with indicators
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                # (qtpylib.crossed_above(dataframe['close'], dataframe['bb_upperband1_1d']))
                (dataframe['close'] > dataframe['bb_middleband1'])
            ),
            'sell'] = 1

        logger.info(f'-----Sell----Pair: {metadata["pair"]}-------------------')
        logger.info(f'\n\n{dataframe.to_markdown()}')

        return dataframe