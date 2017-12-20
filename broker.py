import logging

import pandas as pd

logger = logging.getLogger(__name__)

class Order:
    """
    Attributes:
        side: buy side or sell side order
        type: the type of order (limit or market)
        base: the base currency for the order
        quote: the quote currency for the order
        status: current order status
        price: price the limit order executes at
        size: size of the order
    """


    BUY_SIDE = 'buy'
    SELL_SIDE = 'sell'

    LIMIT_TYPE = 'limit'
    MARKET_TYPE = 'market'

    PENDING_STATUS = 'pending'
    COMPLETED_STATUS = 'completed'
    CANCELLED_STATUS = 'cancelled'


    def __init__(self):
        self.side = None
        self.type = None

        self.base = None
        self.quote = None

        self.credit_account = None
        self.debit_account = None

        self.status = Order.PENDING_STATUS

        self.price = 0.0
        self.size = 0.0
        self.debit_total = 0.0
        self.credit_total = 0.0


class Broker:
    """
    Attributes:
        data: full dataframe for the backtest
        price_column: column in data to use for price
        accounts: dataframe of account values during the backtest
        starting_balances: starting account balances
        index: the current index of the data as the backtest runs
        orders: the list of pending orders
    """

    DEFAULT_FEE = 0.0
    DEFAULT_LIMIT_FEE = 0.0
    DEFAULT_MARKET_FEE = 0.0025

    def __init__(self, data, price_column, accounts, balances,
            limit_fee=DEFAULT_LIMIT_FEE,
            market_fee=DEFAULT_MARKET_FEE):
        """
        :param data: full dataframe for the backtest
        :param price_column: column in data to use for price
        :param accounts: list of account names
        :param balances: list of starting balances of each account
        :param limit_fee: fee for limit orders
        :param market_fee: fee for market orders
        """

        self.data = data
        self.price_column = price_column

        self.accounts = pd.DataFrame(index=data.index, columns=accounts)
        self.starting_balances = balances

        metric_columns = ['Total Value', 'Return', 'Cumulative Return']
        self.metrics = pd.DataFrame(index=data.index, columns=metric_columns)

        self.limit_fee = limit_fee
        self.market_fee = market_fee

        self.index = None

        self.orders = []


    def get_account_balance(self, account):
        balance = self.accounts.loc[self.index, account]

        return balance


    def set_account_balance(self, account, balance):
        self.accounts.loc[self.index, account] = balance


    def populate_account_balances(self):
        """
        Populate the account balances for the current index

        Must be called before any methods that might alter the account balance
        for this iteration in the backtest.
        """

        prev_index = self.accounts.index.get_loc(self.index) - 1

        if prev_index >= 0:
            self.accounts.loc[self.index,:] = self.accounts.iloc[prev_index,:]
        else:
            self.accounts.loc[self.index,:] = self.starting_balances


    def get_current_price(self):
        return self.data.loc[self.index,self.price_column]


    def handle_limit_order(self, order):
        """
        :param order: limit order to process
        """

        current_price = self.get_current_price()

        is_buy_order = order.side == Order.BUY_SIDE
        is_price_greater = order.price >= current_price
        can_buy = is_buy_order and is_price_greater

        is_sell_order = order.side == Order.SELL_SIDE
        is_price_lower = order.price <= current_price
        can_sell = is_sell_order and is_price_lower

        if can_buy or can_sell:
            self.execute_order(order)
        

    def clean_orders(self):
        """
        Remove any orders that have been resolved from the list
        """

        clean_statuses = (
            Order.COMPLETED_STATUS,
            Order.CANCELLED_STATUS,
        )

        cleaned_orders = []

        for order in self.orders:
            if order.status not in clean_statuses:
                cleaned_orders.append(order)

        self.orders = cleaned_orders


    def calculate_total_value(self):
        """
        Calculate total value of all accounts and all pending orders

        TODO: Abstract this from USD and BTC specific accounts
        """

        usd = self.get_account_balance('USD')
        btc = self.get_account_balance('BTC')

        for order in self.orders:
            if order.status == Order.PENDING_STATUS:
                if order.side == Order.BUY_SIDE:
                    usd += order.debit_total
                elif order.side == Order.SELL_SIDE:
                    btc += order.debit_total

        btc_in_usd = btc * self.data.loc[self.index, self.price_column]
        total_value = usd + btc_in_usd

        self.metrics.loc[self.index, 'Total Value'] = total_value


    def handle_data(self, index):
        """
        :param index: the current row index
        :data: the full dataframe
        """

        self.index = index

        self.populate_account_balances()

        for order in self.orders:
            if order.type == Order.LIMIT_TYPE:
                self.handle_limit_order(order)

        self.clean_orders()

        self.calculate_total_value()


    def get_fee(self, order):
        """
        :param order: the order to get fees for
        """

        if order.type == Order.LIMIT_TYPE:
            return self.limit_fee
        elif order.type == Order.MARKET_TYPE:
            return self.market_fee
        else:
            return Broker.DEFAULT_FEE


    def execute_order(self, order):
        """
        :param order: the order to execute
        """

        logger.info('{}:Executed {} {} {}-{} order at {}'.format(
            self.index, order.type, order.side, order.base, order.quote,
            order.price))

        if order.status == Order.PENDING_STATUS:
            balance = self.get_account_balance(order.credit_account)
            balance += order.credit_total

            self.set_account_balance(order.credit_account, balance)

            order.status = Order.COMPLETED_STATUS


    def _place_order(self, order):
        """
        :param order: the order sent to the broker
        """

        balance = self.get_account_balance(order.debit_account)
        fee = order.debit_total * self.get_fee(order)

        if balance > order.debit_total + fee:

            balance -= (order.debit_total + fee)
            self.set_account_balance(order.debit_account, balance)

            logger.info('{}:Placed {} {} {}-{} order at {}'.format(
                self.index, order.type, order.side, order.base, order.quote,
                order.price))

            if order.type == Order.LIMIT_TYPE:
                self.orders.append(order)
            elif order.type == Order.MARKET_TYPE:
                self.execute_order(order)


    def buy_limit(self, base, quote, price, size):
        """
        :param base: the base currency for the order
        :param quote: the quote currency for the order
        :param price: the price of the order
        :param size: the size of the order
        """

        order = Order()
        order.side = Order.BUY_SIDE
        order.type = Order.LIMIT_TYPE
        order.base = base
        order.quote = quote
        order.credit_account = base
        order.debit_account = quote
        order.price = price
        order.size = size
        order.debit_total = price * size
        order.credit_total = size

        self._place_order(order)


    def sell_limit(self, base, quote, price, size):
        """
        :param base: the base currency for the order
        :param quote: the quote currency for the order
        :param price: the price of the order
        :param size: the size of the order
        """

        order = Order()
        order.side = Order.SELL_SIDE
        order.type = Order.LIMIT_TYPE
        order.base = base
        order.quote = quote
        order.credit_account = quote
        order.debit_account = base
        order.price = price
        order.size = size
        order.debit_total = size
        order.credit_total = price * size

        self._place_order(order)


    def buy_market(self, base, quote, size):
        """
        :param base: the base currency for the order
        :param quote: the quote currency for the order
        :param size: the size of the order
        """

        order = Order()
        order.side = Order.BUY_SIDE
        order.type = Order.MARKET_TYPE
        order.base = base
        order.quote = quote
        order.credit_account = base
        order.debit_account = quote

        price = self.get_current_price()

        order.price = price
        order.size = size
        order.debit_total = price * size
        order.credit_total = size

        self._place_order(order)


    def sell_market(self, base, quote, size):
        """
        :param base: the base currency for the order
        :param quote: the quote currency for the order
        :param size: the size of the order
        """

        order = Order()
        order.side = Order.SELL_SIDE
        order.type = Order.MARKET_TYPE
        order.base = base
        order.quote = quote
        order.credit_account = quote
        order.debit_account = base

        price = self.get_current_price()

        order.price = price
        order.size = size
        order.debit_total = size
        order.credit_total = price * size

        self._place_order(order)


    def cancel_order(self, order):
        """
        :param order: the order to cancel
        """

        balance = self.get_account_balance(order.debit_account)
        fee = order.debit_total * self.get_fee(order)
        balance += (order.debit_total + fee)

        self.set_account_balance(order.debit_account, balance)

        order.status = Order.CANCELLED_STATUS

        logger.info('{}:Cancelled {} {}-{} order'.format(self.index, order.side, order.base, order.quote))


    def calculate_metrics(self):
        """
        """

        self.metrics['Return'] = self.metrics['Total Value'].pct_change()
        self.metrics['Cumulative Return'] = (self.metrics['Return'] + 1).cumprod() - 1

        sharpe = self.metrics['Return'].mean() / self.metrics['Return'].std()

        benchmark = self.data[self.price_column].pct_change()
        benchmark_sharpe = benchmark.mean() / benchmark.std()

        print('Sharpe Ratio: {}'.format(sharpe))
        print('Benchmark Sharpe Ratio: {}'.format(benchmark_sharpe))


    def plot(self, axes, data_subplots):
        """
        :param axes: chart axes
        """

        for i, column in enumerate(self.accounts):
            self.accounts[column].plot(ax=axes[data_subplots + i], legend=True)

        self.metrics.plot(subplots=True)
