import logging
import time
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Generator, List

import httpx

from .consts import *
from .exceptions import PanAPIError, PanRateLimitError, PanTokenExpiredError
from .models import (
    FileInfo, FileListResponse, ShareInfo, ShareListResponse, ShareCreateResponse,
    OfflineTaskResponse, OfflineProcessResponse, UserInfo,
    DirectLinkLogResponse, OfflineLogResponse, IpBlacklistResponse
)
from .utils import calculate_file_md5, calculate_bytes_md5, get_file_info

logger = logging.getLogger(__name__)


class PanClient:
    def __init__(
            self,
            client_id: str,
            client_secret: str,
            access_token: Optional[str] = None,
            base_url: str = API_BASE_URL
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._token_expires_at: Optional[datetime] = None
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0, read=120.0, write=None)
        )

    @property
    def access_token(self) -> str:
        """
        :return: access_token
        """
        if self._should_refresh_token():
            logger.info("Access token is missing or expiring, refreshing...")
            self.login()
        return self._access_token or ""

    def _should_refresh_token(self) -> bool:
        if not self._access_token: return True
        if self._token_expires_at:
            now = datetime.now(self._token_expires_at.tzinfo)
            if now >= (self._token_expires_at - timedelta(minutes=5)):
                return True
        return False

    def _get_headers(self, auth_required: bool = True) -> Dict[str, str]:
        headers = {"Platform": PLATFORM_HEADER_VAL, "User-Agent": USER_AGENT}
        if auth_required:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"
        auth_required = kwargs.pop("auth_required", True)
        headers = self._get_headers(auth_required)
        if "headers" in kwargs: headers.update(kwargs.pop("headers"))

        resp_json = {}
        network_retry_limit = 3
        for attempt in range(network_retry_limit):
            response = None
            try:
                response = self.client.request(method, url, headers=headers, **kwargs)

                # QPS 限制处理 (原有逻辑)
                retry_qps = 0
                while retry_qps < MAX_RETRIES and response.json().get("code") == QPS_ERROR_CODE:
                    time.sleep(0.5)
                    response = self.client.request(method, url, headers=headers, **kwargs)
                    retry_qps += 1

                response.raise_for_status()
                resp_json = response.json()
                break  # 成功则跳出重试循环
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == network_retry_limit - 1:
                    raise PanAPIError(0, f"Network Final Error after {network_retry_limit} retries: {str(e)}")
                logger.warning(f"Network issue ({e}), retrying {attempt + 1}/{network_retry_limit}...")
                time.sleep(1 * (attempt + 1))
            except Exception as e:
                raise PanAPIError(0, f"Request Error: {str(e)}")
            finally:
                if response:
                    response.close()
        code = resp_json.get("code")
        if code == 0: return resp_json.get("data")

        trace_id = resp_json.get("x-traceID")
        msg = resp_json.get("message", "")
        if code == 401:
            self._access_token = None
            raise PanTokenExpiredError(code, msg, trace_id)
        elif code == 429:
            raise PanRateLimitError(code, msg, trace_id)
        else:
            raise PanAPIError(code, msg, trace_id)

    def login(self) -> Dict[str, Any]:
        payload:Dict[str, Any] = {"clientID": self.client_id, "clientSecret": self.client_secret}
        data = self._request("POST", API_PATH_ACCESS_TOKEN, json=payload, auth_required=False)
        self._access_token = data["accessToken"]
        if data.get("expiredAt"):
            try:
                self._token_expires_at = datetime.fromisoformat(data.get("expiredAt"))
            except ValueError:
                self._token_expires_at = None
        return data

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== 文件/目录管理 ====================
    def mkdir(self, name: str, parent_id: int = 0, parents=True) -> int:
        """
        创建目录
        :param name: 目录名(注:不能重名)
        :param parent_id: 父目录id，上传到根目录时填写 0
        :param parents: 自动创建父目录（ name 需要包含 / 层级）
        :return: dirID 文件夹ID
        """
        parent_id = parent_id or 0
        if parents:
            dirname_list = name.replace('\\', '/').split("/")
            for dirname in dirname_list:
                data = self._request("POST", API_PATH_MKDIR, json={"name": dirname, "parentID": parent_id})
                parent_id = data.get("dirID")
            return parent_id
        return self._request("POST", API_PATH_MKDIR, json={"name": name, "parentID": parent_id}).get("dirID")

    def rename_file(self, file_id: int, new_name: str) -> bool:
        self._request("PUT", API_PATH_FILE_RENAME_SINGLE, json={"fileId": file_id, "fileName": new_name})
        return True

    def rename_files(self, rename_map: Dict[int, str]) -> bool:
        rename_list = [f"{fid}|{name}" for fid, name in rename_map.items()]
        self._request("POST", API_PATH_FILE_RENAME_BATCH, json={"renameList": rename_list})
        return True

    def move_files(self, file_ids: List[int], to_parent_id: int) -> bool:
        self._request("POST", API_PATH_FILE_MOVE, json={"fileIDs": file_ids, "toParentFileID": to_parent_id})
        return True

    def trash_files(self, file_ids: List[int]) -> bool:
        self._request("POST", API_PATH_FILE_TRASH, json={"fileIDs": file_ids})
        return True

    def delete_files(self, file_ids: List[int]) -> bool:
        self._request("POST", API_PATH_FILE_DELETE, json={"fileIDs": file_ids})
        return True

    def recover_files(self, file_ids: List[int], to_parent_id: Optional[int] = None) -> Dict[str, List[int]]:
        """
        :param file_ids:
        :param to_parent_id:
        :return: 异常文件目录
        """
        ep = API_PATH_FILE_RECOVER_BY_PATH if to_parent_id is not None else API_PATH_FILE_RECOVER
        payload:Dict[str, Any] = {"fileIDs": file_ids}
        if to_parent_id is not None: payload["parentFileID"] = to_parent_id
        return self._request("POST", ep, json=payload)

    # ==================== 信息查询 ====================
    def get_file_detail(self, file_id: int) -> FileInfo:
        data = self._request("GET", API_PATH_FILE_DETAIL, params={"fileID": file_id})
        return FileInfo(**data)

    def get_files_info(self, file_ids: List[int]) -> List[FileInfo]:
        data = self._request("POST", API_PATH_FILE_INFOS, json={"fileIds": file_ids})
        raw_list = data.get("list", []) if isinstance(data, dict) else data
        return [FileInfo(**item) for item in raw_list]

    def list_files(self, parent_id: int = 0, limit: int = 100, last_file_id: int = 0,
                   search_data: str = None) -> FileListResponse:
        params:Dict = {"parentFileId": parent_id, "limit": limit}
        if last_file_id: params["lastFileId"] = last_file_id
        if search_data: params["searchData"] = search_data
        data = self._request("GET", API_PATH_FILE_LIST_V2, params=params)
        return FileListResponse(**data)

    def iter_files(self, parent_id: int = 0, batch_size: int = 100) -> Generator[FileInfo, None, None]:
        last_id = 0
        while True:
            resp = self.list_files(parent_id, batch_size, last_id)
            for f in resp.file_list: yield f
            if resp.last_file_id == -1: break
            last_id = resp.last_file_id

    def get_download_url(self, file_id: int) -> str:
        """
        :return: downloadUrl
        """
        data = self._request("GET", API_PATH_FILE_DOWNLOAD_INFO, params={"fileId": file_id})
        return data["downloadUrl"]

    def get_user_info(self) -> UserInfo:
        """获取当前用户信息"""
        data = self._request("GET", API_PATH_USER_INFO)
        return UserInfo(**data)

    # ==================== 离线下载 ====================
    def offline_download(
            self,
            url: str,
            filename: Optional[str] = None,
            dir_id: Optional[int] = None,
            callback_url: Optional[str] = None
    ) -> OfflineTaskResponse:
        """
        创建离线下载任务
        :param url: http/https 下载地址
        :param filename: 自定义文件名
        :param dir_id: 目标目录ID (不支持根目录)
        :param callback_url: 回调地址
        """
        payload:Dict[str, Any] = {"url": url}
        if filename: payload["fileName"] = filename
        if dir_id: payload["dirID"] = dir_id
        if callback_url: payload["callBackUrl"] = callback_url

        data = self._request("POST", API_PATH_OFFLINE_DOWNLOAD, json=payload)
        return OfflineTaskResponse(**data)

    def get_offline_process(self, task_id: int) -> OfflineProcessResponse:
        """查询离线下载进度"""
        data = self._request("GET", API_PATH_OFFLINE_PROCESS, params={"taskID": task_id})
        return OfflineProcessResponse(**data)

    # ==================== 直链管理 & 日志 ====================
    def get_direct_link_url(self, file_id: int) -> str:
        """
        :return 直链 URL
        """
        data = self._request("GET", API_PATH_DIRECT_LINK_URL, params={"fileID": file_id})
        return data["url"]

    def refresh_direct_link_cache(self) -> bool:
        """刷新直链缓存"""
        self._request("POST", API_PATH_DIRECT_LINK_CACHE_REFRESH, json={})
        return True

    def enable_direct_link_space(self, file_id: int) -> str:
        """启用文件夹直链空间，返回成功启用的文件夹名称"""
        data = self._request("POST", API_PATH_DIRECT_LINK_ENABLE, json={"fileID": file_id})
        return data["filename"]

    def disable_direct_link_space(self, file_id: int) -> str:
        """禁用文件夹直链空间，返回禁用的文件夹名称"""
        data = self._request("POST", API_PATH_DIRECT_LINK_DISABLE, json={"fileID": file_id})
        return data["filename"]

    def get_direct_link_logs(
            self,
            start_time: datetime,
            end_time: datetime,
            page_num: int = 1,
            page_size: int = 100
    ) -> DirectLinkLogResponse:
        """
        获取直链流量日志 (仅限近三天)
        :param page_size:
        :param page_num:
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size,
            "startTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data = self._request("GET", API_PATH_DIRECT_LINK_LOGS, params=params)
        return DirectLinkLogResponse(**data)

    def get_offline_logs(
            self,
            start_time: datetime,
            end_time: datetime,
            page_num: int = 1,
            page_size: int = 100
    ) -> OfflineLogResponse:
        """
        获取直链离线日志 (仅限近30天)
        API 需要的时间格式为 yyyyMMddHH (精确到小时)
        """
        params = {
            "pageNum": page_num,
            "pageSize": page_size,
            "startHour": start_time.strftime("%Y%m%d%H"),
            "endHour": end_time.strftime("%Y%m%d%H")
        }
        data = self._request("GET", API_PATH_OFFLINE_LOGS, json=params)
        return OfflineLogResponse(**data)

    # ==================== 开发者安全配置 ====================
    def switch_ip_blacklist(self, enable: bool) -> bool:
        """开关 IP 黑名单 (True: 启用, False: 禁用)"""
        status = 1 if enable else 2
        data = self._request("POST", API_PATH_DEV_IP_SWITCH, json={"Status": status})
        return data.get("Done", False)

    def update_ip_blacklist(self, ip_list: List[str]) -> bool:
        """
        更新 IP 黑名单列表
        :param ip_list: 最多 2000 个 IPv4 地址
        """
        if len(ip_list) > 2000:
            raise ValueError("IP list exceeds the maximum limit of 2000 addresses.")
        self._request("POST", API_PATH_DEV_IP_UPDATE, json={"IpList": ip_list})
        return True

    def get_ip_blacklist(self) -> IpBlacklistResponse:
        """获取当前 IP 黑名单配置"""
        data = self._request("GET", API_PATH_DEV_IP_LIST)
        return IpBlacklistResponse(**data)

    # ==================== 分享 & 上传 (保留原有逻辑) ====================
    def create_share(self, share_name: str, file_ids: List[int], traffic_switch: Optional[int] = None,
                     traffic_limit_switch: Optional[int] = None, traffic_limit: Optional[int] = None,
                     price: Optional[int] = None, expire_days: int = 0, pwd: Optional[str] = None, is_reward: int = 0,
                     resource_desc: Optional[str] = None) -> ShareCreateResponse:
        file_id_str = ",".join(map(str, file_ids))
        payload:Dict[str, Any] = {"shareName": share_name, "fileIDList": file_id_str}
        if traffic_switch: payload["trafficSwitch"] = traffic_switch
        if traffic_limit_switch: payload["trafficLimitSwitch"] = traffic_limit_switch
        if traffic_limit: payload["trafficLimit"] = traffic_limit

        if price is not None:
            endpoint = API_PATH_PAID_SHARE_CREATE
            payload.update({"payAmount": int(price), "isReward": is_reward, "resourceDesc": resource_desc or ""})
        else:
            endpoint = API_PATH_SHARE_CREATE
            if expire_days not in [0, 1, 7, 30]: raise ValueError("expire_days must be one of [0, 1, 7, 30]")
            payload.update({"shareExpire": expire_days})
            if pwd: payload["sharePwd"] = pwd
        data = self._request("POST", endpoint, json=payload)
        return ShareCreateResponse(**data)

    def list_shares(self, is_paid: bool = False, limit: int = 100, last_share_id: int = 0) -> ShareListResponse:
        endpoint = API_PATH_PAID_SHARE_LIST if is_paid else API_PATH_SHARE_LIST
        params = {"limit": limit}
        if last_share_id: params["lastShareId"] = last_share_id
        data = self._request("GET", endpoint, params=params)
        return ShareListResponse(**data)

    def iter_shares(self, is_paid: bool = False, batch_size: int = 100) -> Generator[ShareInfo, None, None]:
        last_id = 0
        while True:
            resp = self.list_shares(is_paid, batch_size, last_id)
            for s in resp.share_list: yield s
            if resp.last_share_id == -1: break
            last_id = resp.last_share_id

    def update_shares_traffic(self, share_ids: List[int], is_paid: bool = False, traffic_switch: Optional[int] = None,
                              traffic_limit_switch: Optional[int] = None, traffic_limit: Optional[int] = None) -> bool:
        endpoint = API_PATH_PAID_SHARE_UPDATE if is_paid else API_PATH_SHARE_UPDATE
        payload:Dict[str, Any] = {"shareIdList": share_ids}
        if traffic_switch: payload["trafficSwitch"] = traffic_switch
        if traffic_limit_switch: payload["trafficLimitSwitch"] = traffic_limit_switch
        if traffic_limit: payload["trafficLimit"] = traffic_limit
        self._request("PUT", endpoint, json=payload)
        return True

    def get_upload_domain(self) -> str:
        domains = self._request("GET", API_PATH_UPLOAD_DOMAIN)
        if domains and isinstance(domains, list): return domains[0]
        return self.base_url

    def upload_file(self, local_path: str, filename: str = None, parent_file_id: int = 0, conflict_strategy: int = 1) -> int:
        """
        上传文件
        :param filename: 文件名
        :param local_path: 本地文件地址
        :param parent_file_id: 目录id，默认为 0 即根目录
        :param conflict_strategy:
        :return: FileID
        """
        filename = filename.replace('\\', '/')
        while filename.startswith('//'):
            filename = filename[1:]
        if len(final_filename:=filename.split('/')[-1]) >= 255: raise ValueError(f"The filename '{final_filename}' exceeds the 255-character limit")

        if not os.path.exists(local_path): raise FileNotFoundError(f"File not found: {local_path}")
        info = get_file_info(local_path)
        local_file_size, local_filename = info["size"], info["filename"]
        logger.info(f"Preparing upload: {local_filename} ({local_file_size} bytes)")
        file_md5 = calculate_file_md5(local_path)

        while "/" in filename and len(filename) >= 255:
            file_path = filename.split("/")
            parent_file_id = self.mkdir(file_path[0], parent_id = parent_file_id)
            filename = "/".join(file_path[1:])

        if local_file_size < 100 * 1024 * 1024:
            try:
                return self._upload_single(local_path, filename or local_filename, file_md5, local_file_size, parent_file_id, conflict_strategy)
            except PanAPIError:
                pass
        return self._upload_chunked(local_path, filename or local_filename, file_md5, local_file_size, parent_file_id, conflict_strategy)

    def _upload_single(self, filepath, filename, etag, size, parent_id, duplicate) -> int:
        with open(filepath, "rb") as f:
            return self._request(
                "POST",
                f"{self.get_upload_domain().rstrip('/')}{API_PATH_SINGLE_UPLOAD}",
                data={
                    "parentFileID": parent_id,
                    "filename": filename,
                    "etag": etag,
                    "size": size,
                    "duplicate": duplicate,
                    "containDir": True if "/" in filename else False
                },
                files={"file": (filename, f, "application/octet-stream")}
            ).get("fileID")

    def _upload_chunked(self, filepath, filename, etag, size, parent_id, duplicate) -> int:
        init_data = self._request(
            "POST", API_PATH_CHUNK_CREATE,
            json={
                "parentFileID": parent_id,
                "filename": filename,
                "etag": etag,
                "size": size,
                "duplicate": duplicate,
                "containDir": True if "/" in filename else False
            })
        if init_data.get("reuse"):
            logger.info(f"reuse file: {filepath}")
            return init_data.get("fileID")

        pre_id, slice_size, upload_host = init_data["preuploadID"], init_data["sliceSize"], init_data["servers"][0].rstrip("/")
        with open(filepath, "rb") as f:
            slice_no = 1
            while True:
                chunk = f.read(slice_size)
                if not chunk: break

                # 【优化】为单个分片增加重试，防止因单次 Timeout 导致全局失败
                slice_success = False
                upload_timeout = httpx.Timeout(600.0, connect=60.0, write=None)
                for s_retry in range(5):
                    try:
                        self._request("POST", f"{upload_host}{API_PATH_CHUNK_SLICE}",
                                      data={"preuploadID": pre_id, "sliceNo": slice_no,
                                            "sliceMD5": calculate_bytes_md5(chunk)},
                                      files={"slice": ("slice", chunk, "application/octet-stream")},
                                      timeout=upload_timeout
                                      )
                        slice_success = True
                        break
                    except PanAPIError as e:
                        logger.warning(f"Slice {slice_no} failed, retrying... {e}")
                        time.sleep(5)

                if not slice_success:
                    raise PanAPIError(0, f"Chunk {slice_no} upload failed after retries")

                slice_no += 1
        return self._complete_chunked_upload(pre_id)

    def _complete_chunked_upload(self, pre_id: str) -> int:
        for _ in range(60):
            try:
                res = self._request("POST", API_PATH_CHUNK_COMPLETE, json={"preuploadID": pre_id})
                # 如果 code=0 且返回了 completed=True，则成功
                if res.get("completed"):
                    return res.get("fileID")
                # 如果 code=0 但 completed=False (如果有这种情况)，也会走到下面的 sleep

            except PanAPIError as e:
                # 核心修复：捕获 20103 校验中状态，允许重试
                if e.code == 20103:
                    logger.debug(f"服务端校验中 (20103)，等待重试... TraceID: {e.trace_id}")
                else:
                    # 其他错误无法处理，直接抛出
                    raise e
            time.sleep(10)
        raise PanAPIError(0, "Upload merge timed out")

    def transcode_video(self, pan_file_id) -> str:
        self._request(
            "POST",
            API_PATH_TRANSCODE_UPLOAD_FROM_CLOUD_DISK,
            json=[{"fileId": pan_file_id}]
        )
        resolutions = None
        retry = 0
        while retry < 5:
            resolutions = self._request(
                "POST",
                API_PATH_TRANSCODE_VIDEO_RESOLUTIONS,
                json={"fileId": pan_file_id}
            )
            is_get_resolution = resolutions["IsGetResolution"]
            if not is_get_resolution:
                break
            time.sleep(10)
            retry += 1
        if resolutions:
            return self._request("POST", API_PATH_TRANSCODE_VIDEO, json={
                "fileId": pan_file_id,
                "codecName": resolutions['CodecNames'],
                "videoTime": resolutions['VideoTime'],
                "resolutions": resolutions['Resolutions']
            })
        else:
            return "解析视频超时，无法提交转码任务"