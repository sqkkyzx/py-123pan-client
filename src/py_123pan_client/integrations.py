from typing import TYPE_CHECKING

from pydantic import Field
from .consts import *
from .client import PanClient

_DAGSTER_AVAILABLE = False
try:
    from dagster import ConfigurableResource

    _DAGSTER_AVAILABLE = True
except ImportError:
    ConfigurableResource = object

if TYPE_CHECKING:
    try:
        from dagster import ConfigurableResource as DagsterConfigurableResource
    except ImportError:
        DagsterConfigurableResource = object


class Dagster123PanResource(ConfigurableResource):
    """
    123云盘 Dagster 资源集成。

    用于在 Dagster Pipeline/Job 中以 Resource 的形式注入 PanClient。

    使用前请确保已安装 dagster:
        pip install "py-123pan-client[dagster]"
    """

    client_id: str = Field(description="123云盘 API Client ID")
    client_secret: str = Field(description="123云盘 API Client Secret")
    base_url: str = Field(
        default=API_BASE_URL,
        description="API 基础地址，默认为官方开放平台地址"
    )
    upload_bandwidth_mbps: int = Field(
        default=20,
        description="保底上行带宽 (Mbps)，用于动态计算分片上传超时时间"
    )

    def __init__(self, **kwargs):
        if not _DAGSTER_AVAILABLE:
            raise ImportError(
                "Could not import 'dagster'.\n"
                "Please install the dagster extras to use 'Dagster123PanResource':\n\n"
                "    pip install 'py-123pan-client[dagster]'\n"
            )
        super().__init__(**kwargs)

    def get_client(self) -> PanClient:
        """
        获取初始化好的 PanClient 实例。
        通常在 @op 或 @asset 中调用。
        """
        return PanClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
            upload_bandwidth_mbps=self.upload_bandwidth_mbps
        )