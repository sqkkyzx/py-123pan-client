API_BASE_URL = "https://open-api.123pan.com"
PLATFORM_HEADER_VAL = "open_platform"
USER_AGENT = "py-123pan-client/0.1.8"
MAX_RETRIES = 3
QPS_ERROR_CODE = 429

# Auth
API_PATH_ACCESS_TOKEN = "/api/v1/access_token"

# File Management
API_PATH_MKDIR = "/upload/v1/file/mkdir"
API_PATH_UPLOAD_DOMAIN = "/upload/v2/file/domain"

# Upload (V2)
API_PATH_SINGLE_UPLOAD = "/upload/v2/file/single/create"
API_PATH_CHUNK_CREATE = "/upload/v2/file/create"
API_PATH_CHUNK_SLICE = "/upload/v2/file/slice"
API_PATH_CHUNK_COMPLETE = "/upload/v2/file/upload_complete"

# File Operations
API_PATH_FILE_RENAME_SINGLE = "/api/v1/file/name"
API_PATH_FILE_RENAME_BATCH = "/api/v1/file/rename"
API_PATH_FILE_TRASH = "/api/v1/file/trash"
API_PATH_FILE_DELETE = "/api/v1/file/delete"
API_PATH_FILE_RECOVER = "/api/v1/file/recover"
API_PATH_FILE_RECOVER_BY_PATH = "/api/v1/file/recover/by_path"
API_PATH_FILE_MOVE = "/api/v1/file/move"

# File Info
API_PATH_FILE_DETAIL = "/api/v1/file/detail"
API_PATH_FILE_INFOS = "/api/v1/file/infos"
API_PATH_FILE_LIST_V2 = "/api/v2/file/list"
API_PATH_FILE_DOWNLOAD_INFO = "/api/v1/file/download_info"

# Share (Standard)
API_PATH_SHARE_CREATE = "/api/v1/share/create"
API_PATH_SHARE_LIST = "/api/v1/share/list"
API_PATH_SHARE_UPDATE = "/api/v1/share/list/info"

# Share (Paid)
API_PATH_PAID_SHARE_CREATE = "/api/v1/share/content-payment/create"
API_PATH_PAID_SHARE_LIST = "/api/v1/share/payment/list"
API_PATH_PAID_SHARE_UPDATE = "/api/v1/share/list/payment/info"

# Offline Download
API_PATH_OFFLINE_DOWNLOAD = "/api/v1/offline/download"
API_PATH_OFFLINE_PROCESS = "/api/v1/offline/download/process"

# User Info
API_PATH_USER_INFO = "/api/v1/user/info"

# Direct Link (Management)
API_PATH_DIRECT_LINK_URL = "/api/v1/direct-link/url"
API_PATH_DIRECT_LINK_CACHE_REFRESH = "/api/v1/direct-link/cache/refresh"
API_PATH_DIRECT_LINK_ENABLE = "/api/v1/direct-link/enable"
API_PATH_DIRECT_LINK_DISABLE = "/api/v1/direct-link/disable"

# Direct Link (Logs)
API_PATH_DIRECT_LINK_LOGS = "/api/v1/direct-link/log"
API_PATH_OFFLINE_LOGS = "/api/v1/direct-link/offline/logs"

# Developer Security
API_PATH_DEV_IP_SWITCH = "/api/v1/developer/config/forbide-ip/switch"
API_PATH_DEV_IP_UPDATE = "/api/v1/developer/config/forbide-ip/update"
API_PATH_DEV_IP_LIST = "/api/v1/developer/config/forbide-ip/list"


API_PATH_TRANSCODE_UPLOAD_FROM_CLOUD_DISK = "/api/v1/transcode/upload/from_cloud_disk"
API_PATH_TRANSCODE_VIDEO = "/api/v1/transcode/video"
API_PATH_TRANSCODE_VIDEO_RESOLUTIONS = "/api/v1/transcode/video/resolutions"