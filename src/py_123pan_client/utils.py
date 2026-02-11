import hashlib
import os

def calculate_file_md5(file_path: str, chunk_size: int = 8192) -> str:
    """计算文件的 MD5 值 (流式读取)"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()

def calculate_bytes_md5(data: bytes) -> str:
    """计算字节流的 MD5"""
    return hashlib.md5(data).hexdigest()

def get_file_info(file_path: str):
    """获取文件大小和文件名"""
    return {
        "filename": os.path.basename(file_path),
        "size": os.path.getsize(file_path)
    }