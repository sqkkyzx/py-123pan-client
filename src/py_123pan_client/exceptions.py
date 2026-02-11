# src/py_123pan_client/exceptions.py

class PanError(Exception): ...

class PanAPIError(PanError):
    """
    API 返回非 0 code 时的异常
    """
    def __init__(self, code: int, message: str, trace_id: str = None):
        self.code = code
        self.message = message
        self.trace_id = trace_id
        super().__init__(f"[{code}] {message} (TraceID: {trace_id})")

class PanTokenExpiredError(PanAPIError):
    """Access Token 无效 (Code: 401)"""
    pass

class PanRateLimitError(PanAPIError):
    """请求太频繁 (Code: 429)"""
    pass