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


class BB_Hyperopt01(IHyperOpt):
    """
    This is a Hyperopt template to get you started.

    More information in the documentation: https://www.freqtrade.io/en/latest/hyperopt/

    You should:
    - Add any lib you need to build your hyperopt.

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
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy parameters to be used by Hyperopt.
        """
        def populate_buy_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Buy strategy Hyperopt will build and use.
            """
            conditions = []

            if 'buy-trigger' in params:
                for std in range(1, 5):
                    if params['buy-trigger'] == f'buy_bb_lower{std}':
                        conditions.append(dataframe['close'] < dataframe[f'bb_lowerband{std}'])

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
            bollinger_bands.append(f'buy_bb_lower{std}')
        return [
            Categorical(bollinger_bands, name='buy-trigger')
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

            # TRIGGERS
            if 'sell-trigger' in params:
                for std in range(1, 5):
                    if params['sell-trigger'] == f'sell_bb_lower{std}':
                        conditions.append(dataframe['close'] > dataframe[f'bb_lowerband{std}'])
                    if params['sell-trigger'] == f'sell_bb_middle{std}':
                        conditions.append(dataframe['close'] > dataframe[f'bb_middleband{std}'])
                    if params['sell-trigger'] == f'sell_bb_upper{std}':
                        conditions.append(dataframe['close'] > dataframe[f'bb_upperband{std}'])

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
            bollinger_bands.append(f'sell_bb_lower{std}')
            bollinger_bands.append(f'sell_bb_middle{std}')
            bollinger_bands.append(f'sell_bb_upper{std}')
        return [
            Categorical(bollinger_bands, name='sell-trigger')
        ]