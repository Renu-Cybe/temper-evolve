"""
存储后端

提供多种存储后端实现
"""

from pathlib import Path
from typing import Optional, List, Protocol
from datetime import datetime
import shutil
import os


class StorageBackend(Protocol):
    """存储后端协议
    
    所有存储后端必须实现此协议
    """
    
    def save(self, key: str, data: bytes) -> bool:
        """保存数据
        
        Args:
            key: 数据键
            data: 数据内容
            
        Returns:
            是否保存成功
        """
        ...
    
    def load(self, key: str) -> Optional[bytes]:
        """加载数据
        
        Args:
            key: 数据键
            
        Returns:
            数据内容，不存在返回 None
        """
        ...
    
    def delete(self, key: str) -> bool:
        """删除数据
        
        Args:
            key: 数据键
            
        Returns:
            是否删除成功
        """
        ...
    
    def exists(self, key: str) -> bool:
        """检查数据是否存在
        
        Args:
            key: 数据键
            
        Returns:
            是否存在
        """
        ...
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键
        
        Args:
            prefix: 键前缀过滤
            
        Returns:
            键列表
        """
        ...
    
    def get_size(self, key: str) -> int:
        """获取数据大小
        
        Args:
            key: 数据键
            
        Returns:
            数据大小（字节），不存在返回 -1
        """
        ...
    
    def get_modified_time(self, key: str) -> Optional[datetime]:
        """获取修改时间
        
        Args:
            key: 数据键
            
        Returns:
            修改时间，不存在返回 None
        """
        ...


class FileStorageBackend:
    """文件存储后端
    
    基于文件系统的存储实现
    
    使用示例：
        storage = FileStorageBackend("data/storage")
        storage.save("config/app", b"data")
        data = storage.load("config/app")
    """
    
    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, key: str) -> Path:
        """获取文件路径
        
        将key中的/转换为目录结构
        """
        # 安全检查：防止目录遍历
        key = key.replace('..', '_')
        return self._base_dir / key
    
    def save(self, key: str, data: bytes) -> bool:
        """保存数据到文件"""
        try:
            path = self._get_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 原子写入：先写入临时文件，再重命名
            temp_path = path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(data)
            temp_path.rename(path)
            
            return True
        except Exception as e:
            print(f"Storage save error: {e}")
            return False
    
    def load(self, key: str) -> Optional[bytes]:
        """从文件加载数据"""
        try:
            path = self._get_path(key)
            if not path.exists():
                return None
            with open(path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Storage load error: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """删除文件"""
        try:
            path = self._get_path(key)
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            print(f"Storage delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        return self._get_path(key).exists()
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        try:
            if prefix:
                pattern = f"{prefix}*"
                paths = list(self._base_dir.rglob(pattern))
            else:
                paths = list(self._base_dir.rglob("*"))
            
            return [
                str(p.relative_to(self._base_dir))
                for p in paths
                if p.is_file() and not p.suffix == '.tmp'
            ]
        except Exception as e:
            print(f"Storage list error: {e}")
            return []
    
    def get_size(self, key: str) -> int:
        """获取文件大小"""
        try:
            path = self._get_path(key)
            if path.exists():
                return path.stat().st_size
            return -1
        except Exception:
            return -1
    
    def get_modified_time(self, key: str) -> Optional[datetime]:
        """获取文件修改时间"""
        try:
            path = self._get_path(key)
            if path.exists():
                timestamp = path.stat().st_mtime
                return datetime.fromtimestamp(timestamp)
            return None
        except Exception:
            return None
    
    def clear(self, prefix: str = "") -> int:
        """清除数据
        
        Args:
            prefix: 键前缀，空表示全部
            
        Returns:
            删除的文件数
        """
        keys = self.list_keys(prefix)
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count
    
    def get_total_size(self) -> int:
        """获取总存储大小"""
        try:
            total = 0
            for path in self._base_dir.rglob("*"):
                if path.is_file():
                    total += path.stat().st_size
            return total
        except Exception:
            return 0


class MemoryStorageBackend:
    """内存存储后端
    
    用于测试和临时存储，数据不持久化
    
    使用示例：
        storage = MemoryStorageBackend()
        storage.save("key", b"data")
    """
    
    def __init__(self):
        self._data: dict = {}
        self._metadata: dict = {}
    
    def save(self, key: str, data: bytes) -> bool:
        """保存数据到内存"""
        self._data[key] = data
        self._metadata[key] = {
            'size': len(data),
            'modified': datetime.now()
        }
        return True
    
    def load(self, key: str) -> Optional[bytes]:
        """从内存加载数据"""
        return self._data.get(key)
    
    def delete(self, key: str) -> bool:
        """删除数据"""
        if key in self._data:
            del self._data[key]
            del self._metadata[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """检查数据是否存在"""
        return key in self._data
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """列出所有键"""
        if prefix:
            return [k for k in self._data.keys() if k.startswith(prefix)]
        return list(self._data.keys())
    
    def get_size(self, key: str) -> int:
        """获取数据大小"""
        meta = self._metadata.get(key)
        return meta['size'] if meta else -1
    
    def get_modified_time(self, key: str) -> Optional[datetime]:
        """获取修改时间"""
        meta = self._metadata.get(key)
        return meta['modified'] if meta else None
    
    def clear(self) -> None:
        """清空所有数据"""
        self._data.clear()
        self._metadata.clear()
