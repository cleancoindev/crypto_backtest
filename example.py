import logging
import os

import pandas as pd

from crypto_backtest import CryptoBacktest
from strategies.ma_strategy import MAStrategy

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    data = pd.read_csv(
        'data/gdax_history_BTC-USD_60_2017-07-14.csv',
        header=None,
        names=['Time', 'Low', 'High', 'Open', 'Close', 'Volume'],
        index_col='Time',
        parse_dates=True
    )

    data = data.iloc[::-1]

    data = data.resample('H').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
    })

    backtest = CryptoBacktest(data)

    strategy = MAStrategy()
    backtest.add_strategy(strategy)

    backtest.run()

    backtest.plot()
