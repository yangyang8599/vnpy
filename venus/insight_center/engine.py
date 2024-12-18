# venus/insight_center/engine.py

import logging
import traceback
from ast import List
from datetime import datetime
from threading import Thread
from typing import Optional

from vnpy_ctastrategy.backtesting import BacktestingEngine, load_bar_data

from venus.insight_center.base import EVENT_IC_LOG
from vnpy.event import Event
from vnpy.trader.constant import Interval
from vnpy.trader.database import get_database, BaseDatabase
from vnpy.trader.datafeed import get_datafeed, BaseDatafeed
from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine
from vnpy.trader.event import EVENT_TICK
from vnpy.trader.object import TickData, BarData, LogData, HistoryRequest, ContractData
from vnpy.trader.utility import extract_vt_symbol

APP_NAME = "InsightCenter"


class InsightCenterEngine(BaseEngine):
    """
    智析中心引擎逻辑，参考 vnpy_ctastrategy 的 engine.py 结构。
    负责核心业务逻辑、数据处理与事件响应。
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """
        构造函数
        """
        super().__init__(main_engine, event_engine, APP_NAME)

        # 在这里初始化您需要的属性、数据结构
        self.symbol_data = {}  # 示例：存储不同合约的分析数据

        # 注册事件
        self.register_event()


        self.backtesting_engine: BacktestingEngine = None
        self.thread: Thread = None

        self.datafeed: BaseDatafeed = get_datafeed()
        self.database: BaseDatabase = get_database()
        logging.info(f"{APP_NAME} Engine 初始化完成。")
    def init_engine(self) -> None:
        """"""
        self.write_log("初始化IC引擎")

        self.backtesting_engine = BacktestingEngine()
        # Redirect log from backtesting engine outside.
        self.backtesting_engine.output = self.write_log

        self.init_datafeed()
    def init_datafeed(self) -> None:
        """
        Init datafeed client.
        """
        result: bool = self.datafeed.init(self.write_log)
        if result:
            self.write_log("数据服务初始化成功")
    def write_log(self, msg: str) -> None:
        """"""
        event: Event = Event(EVENT_IC_LOG)
        # 如果 msg 是字符串，则转成字典类型
        if isinstance(msg, str):
            # 使用 vn.py 框架中已有的 LogData 数据结构
            event.data = LogData(msg=msg, gateway_name="Venus_IC")
        else:
            # 如果已经是字典或对象，就直接使用
            event.data = msg
        self.event_engine.put(event)

    def register_event(self):
        """
        注册要监听的事件，例如 TICK、BAR、订单事件等
        """
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        # self.event_engine.register(EVENT_BAR, self.process_bar_event)
        logging.info(f"{APP_NAME} Engine 已注册事件监听。")

    def process_tick_event(self, event):
        """
        处理 TICK 事件
        """
        tick: TickData = event.data
        logging.debug(f"[{APP_NAME}] 收到Tick: {tick.symbol}, 价格: {tick.last_price}")

        # 在这里执行对 Tick 数据的处理，比如存储、计算指标等等
        self.symbol_data.setdefault(tick.symbol, []).append(tick.last_price)

    def process_bar_event(self, event):
        """
        处理 BAR 事件
        """
        bar: BarData = event.data
        logging.debug(f"[{APP_NAME}] 收到Bar: {bar.symbol}, 收盘价: {bar.close_price}")

        # 在这里执行对 Bar 数据的处理，比如技术指标计算、策略信号等
        self.symbol_data.setdefault(bar.symbol, []).append(bar.close_price)

    def get_symbol_analysis(self, symbol: str):
        """
        对外暴露一些方法，供界面或其他模块调用，获取分析结果
        """
        data_list = self.symbol_data.get(symbol, [])
        if not data_list:
            return None
        # 简单示例：返回平均值
        return sum(data_list) / len(data_list) if data_list else None

    def run_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> None:
        """
        执行下载任务
        """
        self.write_log(("{}-{}开始下载历史数据").format(vt_symbol, interval))

        try:
            symbol, exchange = extract_vt_symbol(vt_symbol)
        except ValueError:
            self.write_log(("{}解析失败，请检查交易所后缀").format(vt_symbol))
            self.thread = None
            return

        req: HistoryRequest = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=Interval(interval),
            start=start,
            end=end
        )

        try:
            if interval == "tick":
                data: List[TickData] = self.datafeed.query_tick_history(req, self.write_log)
            else:
                contract: Optional[ContractData] = self.main_engine.get_contract(vt_symbol)

                # If history data provided in gateway, then query
                if contract and contract.history_data:
                    data: List[BarData] = self.main_engine.query_history(
                        req, contract.gateway_name
                    )
                # Otherwise use RQData to query data
                else:
                    data: List[BarData] = self.datafeed.query_bar_history(req, self.write_log)

            if data:
                if interval == "tick":
                    self.database.save_tick_data(data)
                else:
                    self.database.save_bar_data(data)

                self.write_log(("{}-{}历史数据下载完成").format(vt_symbol, interval))
            else:
                self.write_log(("数据下载失败，无法获取{}的历史数据").format(vt_symbol))
        except Exception:
            msg: str = ("数据下载失败，触发异常：\n{}").format(traceback.format_exc())
            self.write_log(msg)

        # Clear thread object handler.
        self.thread = None

    def start_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> bool:
        if self.thread:
            self.write_log(("已有任务在运行中，请等待完成"))
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_downloading,
            args=(
                vt_symbol,
                interval,
                start,
                end
            )
        )
        self.thread.start()
        #清除缓存 todo
        load_bar_data.cache_clear()

        return True
    
    def set_backtesting_parameters(self,
        vt_symbol: str,
        interval: Interval,
        start: datetime,
        rate: float,
        slippage: float,
        size: float,
        pricetick: float,
        capital: int,
        end: datetime,
    ):
        self.backtesting_engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
            end=end,
        )
    def get_history_data(self) -> list:
        """"""
        self.backtesting_engine.load_data()
        return self.backtesting_engine.history_data

