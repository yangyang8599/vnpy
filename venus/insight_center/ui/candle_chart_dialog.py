from copy import copy

import pyqtgraph as pg

from vnpy.chart import ChartWidget, CandleItem, VolumeItem
from vnpy.trader.constant import Direction
from vnpy.trader.object import TradeData, BarData
from vnpy.trader.ui import QtGui, QtWidgets, QtCore


class CandleChartDialog(QtWidgets.QDialog):
    """"""

    def __init__(self) -> None:
        """"""
        super().__init__()

        self.updated: bool = False

        self.dt_ix_map: dict = {}
        self.ix_bar_map: dict = {}

        self.high_price = 0
        self.low_price = 0
        self.price_range = 0

        self.items: list = []
        self.symbol = ""  # 你可以通过外部方法设置当前股票/期货代码


        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(("回测K线图表"))
        self.resize(1400, 800)

        # Create chart widget
        self.chart: ChartWidget = ChartWidget()
        self.chart.add_plot("candle", hide_x_axis=True)
        self.chart.add_plot("volume", maximum_height=200)
        # self.chart.add_plot("macd", maximum_height=200)
        self.chart.add_item(CandleItem, "candle", "candle")
        self.chart.add_item(VolumeItem, "volume", "volume")
        # 添加均线
        # 添加均线
        # self.chart.add_item(MovingAverageItem, "ma", "candle")  # 20日均线，颜色为黄色

        self.chart.add_cursor()

        # Create stock code label (symbol display)
        self.symbol_label: QtWidgets.QLabel = QtWidgets.QLabel(f"当前股票/期货代码: {self.symbol}")
        self.symbol_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.symbol_label.setStyleSheet("font-size: 18px; color: white; background-color: black;")

        # Create help widget
        text1: str = ("红色虚线 —— 盈利交易")
        label1: QtWidgets.QLabel = QtWidgets.QLabel(text1)
        label1.setStyleSheet("color:red")

        text2: str = ("绿色虚线 —— 亏损交易")
        label2: QtWidgets.QLabel = QtWidgets.QLabel(text2)
        label2.setStyleSheet("color:#00FF00")

        text3: str = ("黄色向上箭头 —— 买入开仓 Buy")
        label3: QtWidgets.QLabel = QtWidgets.QLabel(text3)
        label3.setStyleSheet("color:yellow")

        text4: str = ("黄色向下箭头 —— 卖出平仓 Sell")
        label4: QtWidgets.QLabel = QtWidgets.QLabel(text4)
        label4.setStyleSheet("color:yellow")

        text5: str = ("紫红向下箭头 —— 卖出开仓 Short")
        label5: QtWidgets.QLabel = QtWidgets.QLabel(text5)
        label5.setStyleSheet("color:magenta")

        text6: str = ("紫红向上箭头 —— 买入平仓 Cover")
        label6: QtWidgets.QLabel = QtWidgets.QLabel(text6)
        label6.setStyleSheet("color:magenta")

        hbox1: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox1.addStretch()
        hbox1.addWidget(label1)
        hbox1.addStretch()
        hbox1.addWidget(label2)
        hbox1.addStretch()

        hbox2: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox2.addStretch()
        hbox2.addWidget(label3)
        hbox2.addStretch()
        hbox2.addWidget(label4)
        hbox2.addStretch()

        hbox3: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox3.addStretch()
        hbox3.addWidget(label5)
        hbox3.addStretch()
        hbox3.addWidget(label6)
        hbox3.addStretch()

        # Set layout
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.symbol_label)  # Add the stock code label at the top
        vbox.addWidget(self.chart)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)
        self.setLayout(vbox)

    def update_history(self, symbol:str, history: list) -> None:
        """"""
        self.updated = True
        self.symbol = symbol
        self.symbol_label.setText(f"当前股票/期货代码: {self.symbol}")
        self.chart.update_history(history)

        for ix, bar in enumerate(history):
            self.ix_bar_map[ix] = bar
            self.dt_ix_map[bar.datetime] = ix

            if not self.high_price:
                self.high_price = bar.high_price
                self.low_price = bar.low_price
            else:
                self.high_price = max(self.high_price, bar.high_price)
                self.low_price = min(self.low_price, bar.low_price)

        self.price_range = self.high_price - self.low_price

    def update_trades(self, trades: list) -> None:
        """"""
        trade_pairs: list = generate_trade_pairs(trades)

        candle_plot: pg.PlotItem = self.chart.get_plot("candle")

        scatter_data: list = []

        y_adjustment: float = self.price_range * 0.001

        for d in trade_pairs:
            open_ix = self.dt_ix_map[d["open_dt"]]
            close_ix = self.dt_ix_map[d["close_dt"]]
            open_price = d["open_price"]
            close_price = d["close_price"]

            # Trade Line
            x: list = [open_ix, close_ix]
            y: list = [open_price, close_price]

            if d["direction"] == Direction.LONG and close_price >= open_price:
                color: str = "r"
            elif d["direction"] == Direction.SHORT and close_price <= open_price:
                color: str = "r"
            else:
                color: str = "g"

            pen: QtGui.QPen = pg.mkPen(color, width=1.5, style=QtCore.Qt.PenStyle.DashLine)
            item: pg.PlotCurveItem = pg.PlotCurveItem(x, y, pen=pen)

            self.items.append(item)
            candle_plot.addItem(item)

            # Trade Scatter
            open_bar: BarData = self.ix_bar_map[open_ix]
            close_bar: BarData = self.ix_bar_map[close_ix]

            if d["direction"] == Direction.LONG:
                scatter_color: str = "yellow"
                open_symbol: str = "t1"
                close_symbol: str = "t"
                open_side: int = 1
                close_side: int = -1
                open_y: float = open_bar.low_price
                close_y: float = close_bar.high_price
            else:
                scatter_color: str = "magenta"
                open_symbol: str = "t"
                close_symbol: str = "t1"
                open_side: int = -1
                close_side: int = 1
                open_y: float = open_bar.high_price
                close_y: float = close_bar.low_price

            pen = pg.mkPen(QtGui.QColor(scatter_color))
            brush: QtGui.QBrush = pg.mkBrush(QtGui.QColor(scatter_color))
            size: int = 10

            open_scatter: dict = {
                "pos": (open_ix, open_y - open_side * y_adjustment),
                "size": size,
                "pen": pen,
                "brush": brush,
                "symbol": open_symbol
            }

            close_scatter: dict = {
                "pos": (close_ix, close_y - close_side * y_adjustment),
                "size": size,
                "pen": pen,
                "brush": brush,
                "symbol": close_symbol
            }

            scatter_data.append(open_scatter)
            scatter_data.append(close_scatter)

            # Trade text
            volume = d["volume"]
            text_color: QtGui.QColor = QtGui.QColor(scatter_color)
            open_text: pg.TextItem = pg.TextItem(f"[{volume}]", color=text_color, anchor=(0.5, 0.5))
            close_text: pg.TextItem = pg.TextItem(f"[{volume}]", color=text_color, anchor=(0.5, 0.5))

            open_text.setPos(open_ix, open_y - open_side * y_adjustment * 3)
            close_text.setPos(close_ix, close_y - close_side * y_adjustment * 3)

            self.items.append(open_text)
            self.items.append(close_text)

            candle_plot.addItem(open_text)
            candle_plot.addItem(close_text)

        trade_scatter: pg.ScatterPlotItem = pg.ScatterPlotItem(scatter_data)
        self.items.append(trade_scatter)
        candle_plot.addItem(trade_scatter)

    def clear_data(self) -> None:
        """"""
        self.updated = False

        candle_plot: pg.PlotItem = self.chart.get_plot("candle")
        for item in self.items:
            candle_plot.removeItem(item)
        self.items.clear()

        self.chart.clear_all()

        self.dt_ix_map.clear()
        self.ix_bar_map.clear()

    def is_updated(self) -> bool:
        """"""
        return self.updated

def generate_trade_pairs(trades: list) -> list:
    """"""
    long_trades: list = []
    short_trades: list = []
    trade_pairs: list = []

    for trade in trades:
        trade: TradeData = copy(trade)

        if trade.direction == Direction.LONG:
            same_direction: list = long_trades
            opposite_direction: list = short_trades
        else:
            same_direction: list = short_trades
            opposite_direction: list = long_trades

        while trade.volume and opposite_direction:
            open_trade: TradeData = opposite_direction[0]

            close_volume = min(open_trade.volume, trade.volume)
            d: dict = {
                "open_dt": open_trade.datetime,
                "open_price": open_trade.price,
                "close_dt": trade.datetime,
                "close_price": trade.price,
                "direction": open_trade.direction,
                "volume": close_volume,
            }
            trade_pairs.append(d)

            open_trade.volume -= close_volume
            if not open_trade.volume:
                opposite_direction.pop(0)

            trade.volume -= close_volume

        if trade.volume:
            same_direction.append(trade)

    return trade_pairs