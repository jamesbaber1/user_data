# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

# --- Do not remove these libs ---
from functools import reduce
from typing import Any, Callable, Dict, List

import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from skopt.space import Categorical, Dimension, Integer, Real  # noqa

from freqtrade.optimize.hyperopt_interface import IHyperOpt

# --------------------------------
# Add your lib to import here
import talib.abstract as ta  # noqa
import freqtrade.vendor.qtpylib.indicators as qtpylib


class SampleHyperOpt(IHyperOpt):
    """
    This is a sample Hyperopt to inspire you.

    More information in the documentation: https://www.freqtrade.io/en/latest/hyperopt/

    You should:
    - Rename the class name to some unique name.
    - Add any methods you want to build your hyperopt.
    - Add any lib you need to build your hyperopt.

    An easier way to get a new hyperopt file is by using
    `freqtrade new-hyperopt --hyperopt MyCoolHyperopt`.

    You must keep:
    - The prototypes for the methods: populate_indicators, indicator_space, buy_strategy_generator.

    The methods roi_space, generate_roi_table and stoploss_space are not required
    and are provided by default.
    However, you may override them if you need 'roi' and 'stoploss' spaces that
    differ from the defaults offered by Freqtrade.
    Sample implementation of these methods will be copied to `user_data/hyperopts` when
    creating the user-data directory using `freqtrade create-userdir --userdir user_data`,
    or is available online under the following URL:
    https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/templates/sample_hyperopt_advanced.py.
    """

    @staticmethod
    def populate_indicators(dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        This method can also be loaded from the strategy, if it doesn't exist in the hyperopt class.
        """
        dataframe['rsi'] = ta.RSI(dataframe)

        for std in range(1, 5):
            # Bollinger bands
            bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=std)
            dataframe[f'bb_lowerband{std}'] = bollinger['lower']
            dataframe[f'bb_middleband{std}'] = bollinger['mid']
            dataframe[f'bb_upperband{std}'] = bollinger['upper']

        for time_period in range(1, 20):
            # TEMA - Triple Exponential Moving Average
            dataframe[f'tema{time_period}'] = ta.TEMA(dataframe, timeperiod=9)

        return dataframe

    @staticmethod
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy parameters to be used by Hyperopt.
        """
        def populate_buy_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Buy strategy Hyperopt will build and use.
            """
            conditions = []

            for time_period in range(1, 20):

                # Check that volume is not 0
                conditions.append(dataframe['volume'] > 0)

                # GUARDS AND TRENDS
                if params.get('rsi-enabled'):
                    conditions.append(qtpylib.crossed_above(dataframe['rsi'], params['rsi-value']))

                # TRIGGERS
                for std in range(1, 5):
                    if 'trigger' in params:
                        if params['trigger'] == f'bb_upper{std}':
                            conditions.append(dataframe[f'tema{time_period}'] <= dataframe[f'bb_upperband{std}'])

                        if params['trigger'] == f'bb_middle{std}':
                            conditions.append(dataframe[f'tema{time_period}'] <= dataframe[f'bb_middleband{std}'])

                        if params['trigger'] == f'bb_lower{std}':
                            conditions.append(dataframe[f'tema{time_period}'] <= dataframe[f'bb_lowerband{std}'])

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'buy'] = 1

                return dataframe

        return populate_buy_trend

    @staticmethod
    def indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching buy strategy parameters.
        """
        bollinger_bands = []
        for std in range(1, 5):
            bollinger_bands.append(f'bb_lower{std}')
            bollinger_bands.append(f'bb_middle{std}')
            bollinger_bands.append(f'bb_upper{std}')

        tema_time_periods = []
        for time_period in range(1, 20):
            tema_time_periods.append(f'tema{time_period}')

        return [
            Integer(5, 50, name='rsi-value'),
            Categorical([True, False], name='rsi-enabled'),
            Categorical(bollinger_bands, name='trigger'),
            Categorical(tema_time_periods, name='tema_time_period')
        ]

    @staticmethod
    def sell_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the sell strategy parameters to be used by Hyperopt.
        """
        def populate_sell_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Sell strategy Hyperopt will build and use.
            """
            conditions = []

            for time_period in range(1, 20):

                # Check that volume is not 0
                conditions.append(dataframe['volume'] > 0)

                # GUARDS AND TRENDS
                if params.get('rsi-enabled'):
                    conditions.append(qtpylib.crossed_above(dataframe['rsi'], params['rsi-value']))

                # TRIGGERS
                for std in range(1, 5):
                    if 'trigger' in params:
                        if params['trigger'] == f'bb_upper{std}':
                            conditions.append(dataframe[f'tema{time_period}'] > dataframe[f'bb_upperband{std}'])

                        if params['trigger'] == f'bb_middle{std}':
                            conditions.append(dataframe[f'tema{time_period}'] > dataframe[f'bb_middleband{std}'])

                        if params['trigger'] == f'bb_lower{std}':
                            conditions.append(dataframe[f'tema{time_period}'] > dataframe[f'bb_lowerband{std}'])

            if conditions:
                dataframe.loc[
                    reduce(lambda x, y: x & y, conditions),
                    'sell'] = 1

            return dataframe

        return populate_sell_trend

    @staticmethod
    def sell_indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching sell strategy parameters.
        """
        bollinger_bands = []
        for std in range(1, 5):
            bollinger_bands.append(f'bb_lower{std}')
            bollinger_bands.append(f'bb_middle{std}')
            bollinger_bands.append(f'bb_upper{std}')

        tema_time_periods = []
        for time_period in range(1, 20):
            tema_time_periods.append(f'tema{time_period}')

        return [
            Integer(30, 100, name='rsi-value'),
            Categorical([True, False], name='rsi-enabled'),
            Categorical(bollinger_bands, name='trigger'),
            Categorical(tema_time_periods, name='tema_time_period')
        ]

    # def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     """
    #     Based on TA indicators. Should be a copy of same method from strategy.
    #     Must align to populate_indicators in this file.
    #     Only used when --spaces does not include buy space.
    #     """
    #     dataframe.loc[
    #         (
    #                 (qtpylib.crossed_above(dataframe['rsi'], 40)) &  # Signal: RSI crosses above 30
    #                 (dataframe['tema'] <= dataframe['bb_middleband']) &  # Guard: tema below BB middle
    #                 (dataframe['tema'] > dataframe['tema'].shift(1)) &  # Guard: tema is raising
    #                 (dataframe['volume'] > 0)  # Make sure Volume is not 0
    #         ),
    #         'buy'] = 1
    #
    #     return dataframe
    #
    # def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    #     """
    #     Based on TA indicators. Should be a copy of same method from strategy.
    #     Must align to populate_indicators in this file.
    #     Only used when --spaces does not include sell space.
    #     """
    #     dataframe.loc[
    #         (
    #                 (qtpylib.crossed_above(dataframe['rsi'], 62)) &  # Signal: RSI crosses above 70
    #                 (dataframe['tema'] > dataframe['bb_middleband']) &  # Guard: tema above BB middle
    #                 (dataframe['tema'] < dataframe['tema'].shift(1)) &  # Guard: tema is falling
    #                 (dataframe['volume'] > 0)  # Make sure Volume is not 0
    #         ),
    #         'sell'] = 1
    #     return dataframe
