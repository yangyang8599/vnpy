# vnpy_tushare_plus/tushare_plus.py
from copy import deepcopy
from typing import List, Dict, Callable, Optional
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts
from pandas import DataFrame

from vnpy_tushare.tushare_datafeed import TushareDatafeed, CHINA_TZ, INTERVAL_ADJUSTMENT_MAP, INTERVAL_VT2TS, \
    to_ts_asset, to_ts_symbol, STOCK_LIST, EXCHANGE_VT2TS

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.utility import round_to

STOCK_LIST.append(Exchange.SH)
EXCHANGE_VT2TS[Exchange.SH] = "SH"
class Datafeed(TushareDatafeed):
    def __init__(self) -> None:
        """
        扩展的 TushareDatafeed 类，添加自定义功能。

        :param token: Tushare Token
        :param proxy: 可选的代理设置
        """
        super().__init__()
        # 初始化任何额外的属性或配置

    def custom_method(self):
        """
        一个示例自定义方法。
        """
        pro = ts.pro_api()
        map = pro.fut_basic(exchange='CFFEX')
        print(map)
        print("这是一个自定义方法。")

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[list[BarData]]:
        """查询k线数据"""
        if not self.inited:
            self.init(output)

        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        interval: Interval = req.interval
        start: datetime = req.start.strftime("%Y-%m-%d %H:%M:%S")
        end: datetime = req.end.strftime("%Y-%m-%d %H:%M:%S")

        ts_symbol: str = to_ts_symbol(symbol, exchange)
        if not ts_symbol:
            return None

        asset: str = to_ts_asset(symbol, exchange)
        if not asset:
            return None

        ts_interval: str = INTERVAL_VT2TS.get(interval)
        if not ts_interval:
            return None

        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[interval]

        try:
            d1: DataFrame = ts.pro_bar(
                ts_code=ts_symbol,
                start_date=start,
                end_date=end,
                asset=asset,
                freq=ts_interval
            )
        except IOError as ex:
            output(f"发生输入/输出错误：{ex.strerror}")
            return []

        df: DataFrame = deepcopy(d1)

        while True:
            if len(d1) != 8000:
                break
            tmp_end: str = d1["trade_time"].values[-1]

            d1 = ts.pro_bar(
                ts_code=ts_symbol,
                start_date=start,
                end_date=tmp_end,
                asset=asset,
                freq=ts_interval
            )
            df = pd.concat([df[:-1], d1])

        bar_keys: list[datetime] = []
        bar_dict: dict[datetime, BarData] = {}
        data: list[BarData] = []

        # 处理原始数据中的NaN值
        df.fillna(0, inplace=True)

        if df is not None:
            for ix, row in df.iterrows():
                if row["open"] is None:
                    continue

                if interval.value == "d":
                    dt: str = row["trade_date"]
                    dt: datetime = datetime.strptime(dt, "%Y%m%d")
                else:
                    dt: str = row["trade_time"]
                    dt: datetime = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") - adjustment

                dt = dt.replace(tzinfo=CHINA_TZ)

                turnover = row.get("amount", 0)
                if turnover is None:
                    turnover = 0

                open_interest = row.get("oi", 0)
                if open_interest is None:
                    open_interest = 0

                bar: BarData = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=round_to(row["open"], 0.000001),
                    high_price=round_to(row["high"], 0.000001),
                    low_price=round_to(row["low"], 0.000001),
                    close_price=round_to(row["close"], 0.000001), #昨收价【除权价，前复权】 https://tushare.pro/document/2?doc_id=27
                    volume=row["vol"],
                    turnover=turnover,
                    open_interest=open_interest,
                    gateway_name="TS"
                )

                bar_dict[dt] = bar

        bar_keys: list = bar_dict.keys()
        bar_keys = sorted(bar_keys, reverse=False)
        for i in bar_keys:
            data.append(bar_dict[i])

        return data
