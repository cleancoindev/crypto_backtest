class NoBrokerError(Exception):
    pass


class Strategy:
    """
    Base class for backtesting strategy

    Attributes:
        data: full dataframe for the backtest
        broker: needs to be set so the strategy can trade
    """


    def __init__(self):
        self.data = None

        self.broker = None


    def initialize(self):
        """
        Initialize strategy

        Can be overridden by user-defined class.
        """

        pass


    def add_broker(self, broker):
        self.broker = broker


    def add_data(self, data):
        self.data = data


    def handle_data_wrapper(self, index):
        """
        Makes call to user-defined `handle_data` method

        :param index: the current row index being handled
        :param data: the full dataframe
        :raises NoBrokerError: raised when no broker instance has been set
        """

        if self.broker == None:
            raise NoBrokerError('Broker must be added to Strategy')

        self.handle_data(index)


    def handle_data(self, index):
        """
        Process next step in data

        Must be overridden in user-defined class.

        :param index: the current row index being handled
        :param data: the full dataframe
        :raises NotImplementedError: raised when not implemented by child class
        """

        raise NotImplementedError('Strategy must implement handle_data method')
