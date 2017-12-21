#!/usr/bin/env python3

import logging

from matplotlib.dates import DateFormatter, MinuteLocator
from matplotlib.finance import candlestick_ohlc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from broker import Account, Broker

logger = logging.getLogger(__name__)


class CryptoBacktest:
    """
    Attributes:
        data: the full dataframe to backtest
        strategies: list of `Strategy` instances to test
        broker: `Broker` instance to trade on the data
    """

    def __init__(self, data):
        """
        TODO: Abstract this from USD and BTC specific accounts

        :param data: dataframe to run backtest on
        """

        self.data = data
        self.strategies = []

        usd_account = Account('USD', 1000)
        btc_account = Account('BTC', 0, 'Close')
        self.broker = Broker(data, [usd_account, btc_account])


    def add_strategy(self, strategy):
        """
        :param strategy: strategy to add to the backtest
        """

        strategy.add_broker(self.broker)
        strategy.add_data(self.data)
        strategy.initialize()

        self.strategies.append(strategy)


    def run(self):
        """
        """

        logger.info('Running strategies...')

        # Run strategies on data
        for index, row in self.data.iterrows():
            self.broker.handle_data(index)

            for strategy in self.strategies:
                strategy.handle_data_wrapper(index)

        logger.info('Calculating metrics...')

        self.broker.calculate_metrics()


    def plot(self):
        """
        TODO: Share X axis with Candlesticks and account data
        """

        account_subplots = self.broker.accounts_df.shape[1]
        data_subplots = 2

        total_rows = account_subplots + data_subplots

        data_ratio = total_rows * 5 / 8
        volume_ratio = total_rows / 8
        account_ratio = total_rows / (4 * account_subplots)
        height_ratios = [data_ratio, volume_ratio] + [account_ratio] * account_subplots

        fig, axes = plt.subplots(
            nrows=total_rows,
            #sharex=True,
            gridspec_kw = {'height_ratios': height_ratios}
        )

        candlestick_ohlc(axes[0], list(zip(
            self.data.index.astype(np.int64) // 10**9,
            self.data['Open'].values,
            self.data['High'].values,
            self.data['Low'].values,
            self.data['Close'].values,
        )), width=32, colorup='g')

        axes[0].xaxis.set_major_locator(MinuteLocator())
        axes[0].xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%i'))

        try:
            self.data['Volume'].plot(ax=axes[1], legend=True)
        except KeyError:
            pass

        self.broker.plot(axes, data_subplots)

        plt.show()
