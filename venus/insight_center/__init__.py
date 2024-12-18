# venus/insight_center/__init__.py

# venus/insight_center/app.py

from pathlib import Path
from vnpy.trader.app import BaseApp
from .engine import InsightCenterEngine, APP_NAME


class InsightCenterApp(BaseApp):
    """
    智析中心应用入口，参考 vnpy_ctastrategy 的 app.py 结构。
    """
    app_name = APP_NAME
    app_module = __module__
    app_path: Path = Path(__file__).parent
    display_name = "智析中心"
    engine_class = InsightCenterEngine           # 指向我们的引擎逻辑类
    widget_name = "InsightCenterManager"         # 指定主界面类的名称（会在UI中自动加载）
    icon_name = str(app_path.joinpath("ui", "analysis.ico" ))                  # 您可以自定义图标名称

