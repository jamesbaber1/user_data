# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from datetime import datetime
from freqtrade.strategy.interface import IStrategy

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import logging
logger = logging.getLogger('freqtrade.worker')
import os


class BB_Strategy03(IStrategy):
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

    # disable dataframe from being checked so we can modify it and it is not invalidated
    disable_dataframe_checks = True

    # These values can be overridden in the "ask_strategy" section in the config.
    use_sell_signal = True
    sell_profit_only = False
    ignore_roi_if_buy_signal = False

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
            'bb_lowerband1_1d': {'color': 'green'},
            'bb_middleband1_1d': {'color': 'red'},
            'bb_upperband1_1d': {'color': 'green'},
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
        informative_time_frame = '1d'
        informative = None

        if not self.dp:
            # Don't do anything if DataProvider is not available.
            return dataframe

        if self.dp:
            if self.dp.runmode.value in ('live', 'dry_run'):
                now = datetime.utcnow()
                time = pd.Timestamp(year=now.year, month=now.month, day=now.day, tz="GMT+0")

                ticker = self.dp.ticker(metadata['pair'])
                new_row = {'date': time, 'open': 1, 'high': 1, 'low': 1, 'close': ticker['last'], 'volume': 1}

                # Get the informative pair
                informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=informative_time_frame)
                informative = informative.append(new_row, ignore_index=True)

        # if not informative:
        #     return dataframe

        # calculate the bollinger bands with 1d candles
        bollinger = qtpylib.bollinger_bands(informative['close'], window=3, stds=1)
        informative[f'bb_lowerband1'] = bollinger['lower']
        informative[f'bb_middleband1'] = bollinger['mid']
        informative[f'bb_upperband1'] = bollinger['upper']

        # Rename columns to be unique
        # Assuming inf_tf = '1d' - then the columns will now be:
        # date_1d, open_1d, high_1d, low_1d, close_1d
        informative.columns = [f"{col}_{informative_time_frame}" for col in informative.columns]

        # sync up dates
        # informative[f'date_{informative_time_frame}'] = pd.to_datetime(informative[f'date_{informative_time_frame}'], utc=True)
        # dataframe['date'] = pd.to_datetime(dataframe['date'], utc=True)

        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 300)
        logger.info(f'---------Informative Pair: {metadata["pair"]}-------------------')
        path = os.path.normpath(os.path.abspath(os.path.join(os.getcwd(), 'user_data', f"dataframe_{metadata['pair'].replace('/', '')}.csv")))
        logger.info(path)
        file = open(path, "w")
        file.write(dataframe.to_csv())
        file.close()

        logger.info(f'\n\n{informative.to_markdown()}')

        # Combine the 2 dataframes
        # all indicators on the informative sample MUST be calculated before this point
        dataframe = dataframe.merge(
            informative,
            left_on='date',
            right_on=f'date_{informative_time_frame}',
            how='left'
        )

        # FFill to have the 1d value available in every row throughout the day.
        # Without this, comparisons would only work once per day.
        # dataframe = dataframe.ffill()

        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 300)
        logger.info(f'---------Dataframe Pair: {metadata["pair"]}-------------------')
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
                (dataframe['close'] < dataframe['bb_lowerband1_1d']) #&
                # (dataframe['volume'] > self.config['stake_amount'])
            ),
            'buy'] = 1

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
                (dataframe['close'] > dataframe['bb_upperband1_1d']) #&
                # (dataframe['volume'] > self.config['stake_amount'])
            ),
            'sell'] = 1

        return dataframe