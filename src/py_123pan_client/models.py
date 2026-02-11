from typing import List, Optional
from pydantic import BaseModel, Field, AliasChoices


class FileInfo(BaseModel):
    """文件/文件夹信息模型"""
    file_id: int = Field(validation_alias=AliasChoices('fileId', 'fileID', 'file_id'))
    filename: Optional[str] = Field(default=None)
    type: Optional[int] = Field(default=None)
    size: Optional[int] = Field(default=None)
    etag: Optional[str] = Field(default=None)
    status: Optional[int] = Field(default=None)
    parent_file_id: Optional[int] = Field(validation_alias=AliasChoices('parentFileId', 'parentFileID'), default=None)
    create_at: str = Field(validation_alias=AliasChoices('createAt', 'create_at'), default=None)
    trashed: Optional[int] = Field(default=None)
    category: Optional[int] = Field(default=None) # 仅在列表或infos中出现
    download_url: Optional[str] = Field(default=None) # 仅在下载详情时逻辑补充

    @property
    def is_folder(self) -> bool:
        return self.type == 1

class FileListResponse(BaseModel):
    last_file_id: int = Field(validation_alias=AliasChoices('lastFileId'))
    file_list: List[FileInfo] = Field(validation_alias=AliasChoices('fileList'))


class DownloadInfoResponse(BaseModel):
    download_url: str = Field(validation_alias=AliasChoices('downloadUrl'))


class ShareInfo(BaseModel):
    """分享链接信息 (合并了普通分享和付费分享的字段)"""
    share_id: int = Field(validation_alias=AliasChoices('shareId', 'shareID'))
    share_key: str = Field(validation_alias=AliasChoices('shareKey'))
    share_name: str = Field(validation_alias=AliasChoices('shareName'))
    expiration: Optional[str] = None  # 付费分享创建时不返回，列表返回
    expired: Optional[int] = None  # 0 未失效, 1 失效

    # 普通分享特有
    share_pwd: Optional[str] = Field(default=None, validation_alias=AliasChoices('sharePwd'))

    # 付费分享特有
    pay_amount: Optional[float] = Field(default=None, validation_alias=AliasChoices('payAmount'))
    amount: Optional[float] = None  # 收益

    # 流量相关
    traffic_switch: Optional[int] = Field(default=None, validation_alias=AliasChoices('trafficSwitch'))
    traffic_limit_switch: Optional[int] = Field(default=None, validation_alias=AliasChoices('trafficLimitSwitch'))
    traffic_limit: Optional[int] = Field(default=None, validation_alias=AliasChoices('trafficLimit'))
    bytes_charge: Optional[int] = Field(default=None, validation_alias=AliasChoices('bytesCharge'))

    # 统计
    preview_count: Optional[int] = Field(default=0, validation_alias=AliasChoices('previewCount'))
    download_count: Optional[int] = Field(default=0, validation_alias=AliasChoices('downloadCount'))
    save_count: Optional[int] = Field(default=0, validation_alias=AliasChoices('saveCount'))

    @property
    def url(self) -> str:
        """根据是否付费推断 URL 前缀"""
        # 注意：这里仅作简单判断，实际应根据 context，或者 API 返回结果拼接
        # 普通分享: https://www.123pan.com/s/{key}
        # 付费分享: https://www.123pan.com/ps/{key}
        # 由于模型里无法准确区分来源，建议使用 share_key 自行拼接，或者依赖 Create 返回的逻辑
        return f"https://www.123pan.com/s/{self.share_key}"


class ShareListResponse(BaseModel):
    last_share_id: int = Field(validation_alias=AliasChoices('lastShareId'))
    share_list: List[ShareInfo] = Field(validation_alias=AliasChoices('shareList'))


class ShareCreateResponse(BaseModel):
    share_id: int = Field(validation_alias=AliasChoices('shareId', 'shareID'))
    share_key: str = Field(validation_alias=AliasChoices('shareKey'))

# --- 离线下载模型 ---
class OfflineTaskResponse(BaseModel):
    task_id: int = Field(validation_alias=AliasChoices('taskID'))

class OfflineProcessResponse(BaseModel):
    process: float
    status: int # 0进行中、1下载失败、2下载成功、3重试中

# --- 用户信息模型 ---
class VipDetail(BaseModel):
    vip_level: int = Field(validation_alias=AliasChoices('vipLevel'))
    vip_label: str = Field(validation_alias=AliasChoices('vipLabel'))
    start_time: str = Field(validation_alias=AliasChoices('startTime'))
    end_time: str = Field(validation_alias=AliasChoices('endTime'))

class DeveloperInfo(BaseModel):
    start_time: str = Field(validation_alias=AliasChoices('startTime'))
    end_time: str = Field(validation_alias=AliasChoices('endTime'))

class UserInfo(BaseModel):
    uid: int
    nickname: str
    head_image: str = Field(validation_alias=AliasChoices('headImage'))
    passport: str
    mail: str
    space_used: int = Field(validation_alias=AliasChoices('spaceUsed'))
    space_permanent: int = Field(validation_alias=AliasChoices('spacePermanent'))
    space_temp: int = Field(validation_alias=AliasChoices('spaceTemp'))
    vip: bool
    direct_traffic: int = Field(validation_alias=AliasChoices('directTraffic')) # 剩余直链流量
    https_count: int = Field(validation_alias=AliasChoices('httpsCount'))
    vip_info: Optional[List[VipDetail]] = Field(default=None, validation_alias=AliasChoices('vipInfo'))
    developer_info: Optional[DeveloperInfo] = Field(default=None, validation_alias=AliasChoices('developerInfo'))

# --- 直链日志模型 ---
class DirectLinkLogItem(BaseModel):
    unique_id: str = Field(validation_alias=AliasChoices('uniqueID'))
    filename: str = Field(validation_alias=AliasChoices('fileName'))
    file_size: int = Field(validation_alias=AliasChoices('fileSize'))
    file_path: str = Field(validation_alias=AliasChoices('filePath'))
    direct_link_url: str = Field(validation_alias=AliasChoices('directLinkURL'))
    file_source: int = Field(validation_alias=AliasChoices('fileSource')) # 1全部文件 2图床
    total_traffic: int = Field(validation_alias=AliasChoices('totalTraffic'))

class DirectLinkLogResponse(BaseModel):
    total: int
    log_list: List[DirectLinkLogItem] = Field(validation_alias=AliasChoices('list'))

class OfflineLogItem(BaseModel):
    id: str # 文档示例是数字，但有些系统ID可能是字符串，这里宽容处理
    filename: str = Field(validation_alias=AliasChoices('fileName'))
    file_size: int = Field(validation_alias=AliasChoices('fileSize'))
    log_time_range: str = Field(validation_alias=AliasChoices('logTimeRange'))
    download_url: str = Field(validation_alias=AliasChoices('downloadURL'))

class OfflineLogResponse(BaseModel):
    total: int
    log_list: List[OfflineLogItem] = Field(validation_alias=AliasChoices('list'))

# --- 开发者配置模型 ---
class IpBlacklistResponse(BaseModel):
    ip_list: List[str] = Field(validation_alias=AliasChoices('ipList'))
    status: int # 2禁用 1启用