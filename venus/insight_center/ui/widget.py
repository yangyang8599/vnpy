# venus/insight_center/ui/widget.py

import logging
from copy import copy
from datetime import datetime, timedelta

import pyqtgraph as pg

from PySide6 import QtGui

from vnpy.chart import ChartWidget, CandleItem, VolumeItem
from vnpy.event import EventEngine
from vnpy.trader.constant import Direction, Interval, Exchange
from vnpy.trader.database import DB_TZ
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtWidgets, QtCore, Qt
from vnpy.trader.object import BarData, TickData, TradeData
from typing import TYPE_CHECKING, List
from vnpy.trader.ui.widget import (
    BaseCell,
    EnumCell,
    MsgCell,
    TimeCell,
    BaseMonitor
)
from vnpy.trader.utility import save_json
from ..base import EVENT_IC_LOG

from ..engine import InsightCenterEngine, APP_NAME
from ..tool import createButton
from ...ui.ma_chart_item import MovingAverageItem


class InsightCenterManager(QtWidgets.QWidget):
    """
    智析中心管理界面，参考 cta_strategy/ui/widget.py
    """
    setting_filename: str = "insight_center_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.insight_engine = main_engine.get_engine(APP_NAME)

        self.setWindowTitle("智析中心")
        self.init_ui()
        self.insight_engine.init_engine()
        self.write_log = self.insight_engine.write_log

    def init_ui(self):
        """
        初始化界面布局和组件
        """
        """"""
        self.setWindowTitle("智析中心")
        self.setGeometry(100, 100, 1800, 600)  # 设置窗口初始大小，1800px 宽，600px 高

        #工具栏和主要布局区添加到主窗口的布局中。
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(self.create_top_toolbar())
        vbox.addLayout(self.create_main_grid())
        self.setLayout(vbox)

        #弹出的K线窗口：
        self.candle_dialog: CandleChartDialog = CandleChartDialog()


    def create_top_toolbar(self):
        # 顶部工具栏
        topToolbar: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        createButton('启动引擎', topToolbar, None)
        createButton('清空日志', topToolbar, None)
        createButton('测试下载数据', topToolbar, self.test_download_data)
        createButton('测试期货代码', topToolbar, self.test_code)
        createButton('测试K线图', topToolbar, self.show_candle_chart)
        topToolbar.addStretch()
        return topToolbar
    def create_main_grid(self):
        #下面主要内容网格布局区域
        main_grid: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        # main_grid.setColumnStretch(0, 0)
        # main_grid.setColumnStretch(1, 0)
        # main_grid.setColumnStretch(2, 0)
        # main_grid.setColumnStretch(3, 0)
        # main_grid.setColumnStretch(4, 1)
        main_grid.addWidget(self.create_main_left_top_settings(), 0, 0, 4, 4)
        main_grid.addWidget(self.create_main_left_scroll_area(), 4, 0, 2, 4)
        main_grid.addWidget(self.create_main_right_log_monitor(), 0, 4)
        return main_grid
    def create_main_right_log_monitor(self):
        self.log_monitor: LogMonitor = LogMonitor(self.main_engine, self.event_engine)
        return self.log_monitor
    def create_main_left_top_settings(self):
        self.class_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()

        # 替换 QLineEdit 为 QComboBox
        self.symbol_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)  # 不允许重复插入
        self.symbol_combo.setDuplicatesEnabled(False)  # 不允许重复项
        self.symbol_combo.setEditText("IF2503.CFFEX")  # 设置默认文本

        # 如果有预定义的符号列表，可以在此处添加
        predefined_symbols = [
            "IH2501.CFFEX","IH2503.CFFEX","IH2506.CFFEX",
            "IF2501.CFFEX","IF2503.CFFEX", "IF2506.CFFEX",
            "IC2501.CFFEX","IC2503.CFFEX", "IC2506.CFFEX",
            "IM2501.CFFEX", "IM2503.CFFEX","IM2506.CFFEX",
            "000016.SH", "000300.SH", "000905.SH", "000852.SH", "399303.SH","000001.SZSE", "600000.SSE"]  # 示例符号
        self.symbol_combo.addItems(predefined_symbols)

        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for interval in Interval:
            self.interval_combo.addItem(interval.value)

        end_dt: datetime = datetime.now()
        start_dt: datetime = end_dt - timedelta(days=1 * 20)

        self.start_date_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate(
                start_dt.year,
                start_dt.month,
                start_dt.day
            )
        )
        self.end_date_edit: QtWidgets.QDateEdit = QtWidgets.QDateEdit(
            QtCore.QDate.currentDate().addDays(1)
        )

        self.rate_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit("0.000025")
        self.slippage_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit("0.2")
        self.size_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit("300")
        self.pricetick_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit("0.2")
        self.capital_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit("1000000")
        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow(("交易策略"), self.class_combo)
        form.addRow(("本地代码"), self.symbol_combo)
        form.addRow(("K线周期"), self.interval_combo)
        form.addRow(("开始日期"), self.start_date_edit)
        form.addRow(("结束日期"), self.end_date_edit)
        form.addRow(("手续费率"), self.rate_line)
        form.addRow(("交易滑点"), self.slippage_line)
        form.addRow(("合约乘数"), self.size_line)
        form.addRow(("价格跳动"), self.pricetick_line)
        form.addRow(("回测资金"), self.capital_line)
        left_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        left_widget.setLayout(form)
        return left_widget

    def create_main_left_scroll_area(self):
        self.scroll_layout: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        self.scroll_layout.addStretch()
        scroll_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area: QtWidgets.QScrollArea = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_widget)
        return  self.scroll_area

    def refresh_data(self):
        """
        刷新展示
        """
        logging.info("刷新智析中心数据...")
        all_symbols = list(self.insight_engine.symbol_data.keys())
        self.table_analysis.setRowCount(len(all_symbols))

        for row, symbol in enumerate(all_symbols):
            avg_price = self.insight_engine.get_symbol_analysis(symbol) or 0
            item_symbol = QtWidgets.QTableWidgetItem(symbol)
            item_avg = QtWidgets.QTableWidgetItem(str(round(avg_price, 4)))
            self.table_analysis.setItem(row, 0, item_symbol)
            self.table_analysis.setItem(row, 1, item_avg)
    def obtain_config(self):
        class_name: str = self.class_combo.currentText()
        # if not class_name:
        #     self.write_log(("请选择要回测的策略"))
        #     return

        vt_symbol: str = self.symbol_combo.currentText()
        interval: str = self.interval_combo.currentText()
        start: datetime = self.start_date_edit.dateTime().toPython()
        end: datetime = self.end_date_edit.dateTime().toPython()
        rate: float = float(self.rate_line.text())
        slippage: float = float(self.slippage_line.text())
        size: float = float(self.size_line.text())
        pricetick: float = float(self.pricetick_line.text())
        capital: float = float(self.capital_line.text())

        # Check validity of vt_symbol
        if "." not in vt_symbol:
            self.write_log(("本地代码缺失交易所后缀，请检查"))
            return

        __, exchange_str = vt_symbol.split(".")
        if exchange_str not in Exchange.__members__:
            self.write_log(("本地代码的交易所后缀不正确，请检查"))
            return

        # Save backtesting parameters
        insight_center_setting: dict = {
            # "class_name": class_name,
            "vt_symbol": vt_symbol,
            "interval": interval,
            "start": start,
            "rate": rate,
            "slippage": slippage,
            "size": size,
            "pricetick": pricetick,
            "capital": capital,
            "end": end,
        }
        # save_json(self.setting_filename, insight_center_setting)
        return insight_center_setting
    def clear_log(self) -> None:
        """"""
        self.log_monitor.setRowCount(0)
    def test_code(self):
        self.insight_engine.datafeed.custom_method()

    def test_download_data(self):
        conf = self.obtain_config()
        if conf is not None:
            self.insight_engine.set_backtesting_parameters(**conf)
        """"""
        vt_symbol: str = self.symbol_combo.currentText()
        interval: str = self.interval_combo.currentText()
        start_date: QtCore.QDate = self.start_date_edit.date()
        end_date: QtCore.QDate = self.end_date_edit.date()

        start: datetime = datetime(
            start_date.year(),
            start_date.month(),
            start_date.day(),
        )
        start: datetime = start.replace(tzinfo=DB_TZ)

        end: datetime = datetime(
            end_date.year(),
            end_date.month(),
            end_date.day(),
            23,
            59,
            59,
        )
        end: datetime = end.replace(tzinfo=DB_TZ)

        self.insight_engine.start_downloading(
            vt_symbol,
            interval,
            start,
            end
        )
    def show_candle_chart(self) -> None:
        """"""
        # if not self.candle_dialog.is_updated():
        #     self.insight_engine.set_backtesting_parameters(**self.obtain_config())
        #     history: list = self.insight_engine.get_history_data()
        #     self.candle_dialog.update_history(history)
        #
        #     # trades: List[TradeData] = self.insight_engine.get_all_trades()
        #     # self.candle_dialog.update_trades(trades)
        # else:
        self.candle_dialog.clear_data()
        self.insight_engine.set_backtesting_parameters(**self.obtain_config())
        history: list = self.insight_engine.get_history_data()
        self.candle_dialog.update_history(self.symbol_combo.currentText(), history)

        self.candle_dialog.exec()

class LogMonitor(BaseMonitor):
    """
    Monitor for log data.
    """

    event_type: str = EVENT_IC_LOG
    data_key: str = ""
    sorting: bool = False

    headers: dict = {
        "time": {"display": "时间", "cell": TimeCell, "update": False},
        "msg": {"display": "信息", "cell": MsgCell, "update": False},
        "gateway_name": {"display": "接口", "cell": BaseCell, "update": False},
    }

    def init_ui(self) -> None:
        """
        Stretch last column.
        """
        super(LogMonitor, self).init_ui()

        self.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )

    def insert_new_row(self, data) -> None:
        """
        Insert a new row at the top of table.
        """
        super(LogMonitor, self).insert_new_row(data)
        self.resizeRowToContents(0)
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