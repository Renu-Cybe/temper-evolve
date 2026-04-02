"""
持久化系统 - 复利原则的核心实现

设计原则：
1. 能力持久化：学习到的能力保存到磁盘
2. 状态可恢复：支持快照和回滚
3. 多后端支持：文件、数据库等
4. 序列化灵活：JSON、MessagePack等
"""

from .serializers import Serializer, JSONSerializer, PickleSerializer
from .storage import StorageBackend, FileStorageBackend
from .snapshot import Snapshot, SnapshotManager

__all__ = [
    'Serializer', 'JSONSerializer', 'PickleSerializer',
    'StorageBackend', 'FileStorageBackend',
    'Snapshot', 'SnapshotManager',
]
