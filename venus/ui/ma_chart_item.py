from typing import Tuple, List

import pyqtgraph as pg  # 确保导入 pyqtgraph 并命名为 pg

from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from vnpy.chart.item import ChartItem
from vnpy.chart.manager import BarManager
from vnpy.trader.object import BarData


# 在您的 MovingAverageItem 类中进行以下修改

class MovingAverageItem(ChartItem):
    """
    均线图形项，用于绘制移动平均线（MA）。
    """

    def __init__(self, manager: BarManager, window: int=5, color: str='r') -> None:
        """
        初始化均线图形项。

        :param manager: BarManager 实例，用于获取历史数据。
        :param window: 均线的窗口期，例如20表示20日均线。
        :param color: 均线颜色。
        """
        self.window = window
        self.color = color
        super().__init__(manager)

        # 立即计算并初始化均线数据
        ma_values = self._manager.get_precomputed_ma(window=self.window)

        # 初始化 PlotDataItem
        self.plot_data_item = pg.PlotDataItem(
            x=list(range(len(ma_values))),
            y=ma_values,
            pen=pg.mkPen(color=self.color, width=2),
            name=f"MA{window}"
        )

    def boundingRect(self) -> QtCore.QRectF:
        """
        获取均线图形项的边界矩形。
        """
        ma_values = self._manager.get_precomputed_ma(window=self.window)
        if not ma_values:
            return QtCore.QRectF()
        min_ma = min(ma for ma in ma_values if ma is not None)
        max_ma = max(ma for ma in ma_values if ma is not None)
        rect = QtCore.QRectF(
            0,
            min_ma,
            len(ma_values),
            max_ma - min_ma
        )
        return rect

    def get_y_range(self, min_ix: int = None, max_ix: int = None) -> Tuple[float, float]:
        """
        获取均线的 y 轴范围。
        """
        ma_values = self._manager.get_precomputed_ma(window=self.window)
        if not ma_values:
            return (0, 1)
        min_ma = min(ma for ma in ma_values if ma is not None)
        max_ma = max(ma for ma in ma_values if ma is not None)
        return (min_ma, max_ma)

    def get_info_text(self, ix: int) -> str:
        """
        获取鼠标悬停时显示的均线信息。
        """
        ma_values = self._manager.get_precomputed_ma(window=self.window)
        if ix < self.window - 1 or ix >= len(ma_values):
            return ""
        ma = ma_values[ix]
        return f"MA{self.window}: {ma:.2f}"

    def update_history(self, history: List[BarData]) -> None:
        """
        更新历史数据并重绘均线。
        """
        super().update_history(history)
        self.update_ma()

    def update_bar(self, bar: BarData) -> None:
        """
        更新单个Bar数据并重绘均线。
        """
        super().update_bar(bar)
        self.update_ma()

    def update_ma(self) -> None:
        """
        更新均线数据并重绘。
        """
        ma_values = self._manager.get_precomputed_ma(window=self.window)
        # 更新数据
        x = list(range(len(ma_values)))
        y = ma_values
        self.plot_data_item.setData(x=x, y=y)
