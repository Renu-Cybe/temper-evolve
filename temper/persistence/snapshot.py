"""
快照管理器

提供系统状态的快照和恢复功能
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json
import hashlib
import shutil


@dataclass
class Snapshot:
    """快照对象
    
    Attributes:
        id: 快照唯一标识
        timestamp: 创建时间
        description: 描述信息
        state_hash: 状态数据哈希
        metadata: 额外元数据
        tags: 标签列表
    """
    id: str
    timestamp: datetime
    description: str
    state_hash: str
    metadata: Dict[str, Any]
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'state_hash': self.state_hash,
            'metadata': self.metadata,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Snapshot':
        """从字典创建"""
        return cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            description=data['description'],
            state_hash=data['state_hash'],
            metadata=data.get('metadata', {}),
            tags=data.get('tags', [])
        )


class SnapshotManager:
    """快照管理器
    
    管理系统状态的快照，支持创建、恢复、删除和清理
    
    使用示例：
        manager = SnapshotManager("data/snapshots")
        
        # 创建快照
        state_data = serialize_system_state()
        snapshot = manager.create(state_data, "Before major update")
        
        # 恢复快照
        restored_data = manager.restore(snapshot.id)
        
        # 列出快照
        snapshots = manager.list_snapshots()
        
        # 清理旧快照
        manager.cleanup_old_snapshots(max_count=10)
    """
    
    def __init__(self, storage_dir: str = "data/snapshots"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir = self._storage_dir / "states"
        self._state_dir.mkdir(exist_ok=True)
        self._index_file = self._storage_dir / "index.json"
        self._snapshots: Dict[str, Snapshot] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """加载快照索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for snap_data in data.get('snapshots', []):
                        try:
                            snapshot = Snapshot.from_dict(snap_data)
                            self._snapshots[snapshot.id] = snapshot
                        except Exception:
                            continue
            except Exception as e:
                print(f"Failed to load snapshot index: {e}")
    
    def _save_index(self) -> None:
        """保存快照索引"""
        try:
            data = {
                'snapshots': [s.to_dict() for s in self._snapshots.values()],
                'updated_at': datetime.now().isoformat()
            }
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save snapshot index: {e}")
    
    def create(self, 
               state_data: bytes,
               description: str = "",
               metadata: Dict[str, Any] = None,
               tags: List[str] = None) -> Snapshot:
        """创建快照
        
        Args:
            state_data: 状态数据（字节）
            description: 描述信息
            metadata: 额外元数据
            tags: 标签列表
            
        Returns:
            创建的快照对象
        """
        import uuid
        
        snapshot_id = str(uuid.uuid4())[:8]
        state_hash = hashlib.sha256(state_data).hexdigest()[:16]
        
        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            description=description,
            state_hash=state_hash,
            metadata=metadata or {},
            tags=tags or []
        )
        
        # 保存状态数据
        state_file = self._state_dir / f"{snapshot_id}.dat"
        with open(state_file, 'wb') as f:
            f.write(state_data)
        
        # 更新索引
        self._snapshots[snapshot_id] = snapshot
        self._save_index()
        
        return snapshot
    
    def restore(self, snapshot_id: str) -> Optional[bytes]:
        """恢复快照
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            状态数据，不存在返回 None
        """
        if snapshot_id not in self._snapshots:
            return None
        
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if not state_file.exists():
            return None
        
        try:
            with open(state_file, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to restore snapshot {snapshot_id}: {e}")
            return None
    
    def delete(self, snapshot_id: str) -> bool:
        """删除快照
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            是否删除成功
        """
        if snapshot_id not in self._snapshots:
            return False
        
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception as e:
                print(f"Failed to delete snapshot file: {e}")
                return False
        
        del self._snapshots[snapshot_id]
        self._save_index()
        
        return True
    
    def list_snapshots(self, 
                       tag: Optional[str] = None,
                       limit: int = None) -> List[Snapshot]:
        """列出快照
        
        Args:
            tag: 按标签过滤
            limit: 返回数量限制
            
        Returns:
            快照列表（按时间倒序）
        """
        snapshots = list(self._snapshots.values())
        
        if tag:
            snapshots = [s for s in snapshots if tag in s.tags]
        
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        if limit:
            snapshots = snapshots[:limit]
        
        return snapshots
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """获取快照信息"""
        return self._snapshots.get(snapshot_id)
    
    def cleanup_old_snapshots(self, 
                              max_count: int = 10,
                              max_age_days: int = None) -> int:
        """清理旧快照
        
        Args:
            max_count: 保留的最大数量
            max_age_days: 最大保留天数
            
        Returns:
            删除的快照数
        """
        deleted = 0
        
        snapshots = self.list_snapshots()
        
        # 按数量清理
        if len(snapshots) > max_count:
            for snapshot in snapshots[max_count:]:
                if self.delete(snapshot.id):
                    deleted += 1
        
        # 按时间清理
        if max_age_days:
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(days=max_age_days)
            for snapshot in snapshots:
                if snapshot.timestamp < cutoff:
                    if self.delete(snapshot.id):
                        deleted += 1
        
        return deleted
    
    def verify(self, snapshot_id: str) -> bool:
        """验证快照完整性
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            是否完整
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if not state_file.exists():
            return False
        
        try:
            with open(state_file, 'rb') as f:
                data = f.read()
            
            # 验证哈希
            actual_hash = hashlib.sha256(data).hexdigest()[:16]
            return actual_hash == snapshot.state_hash
        except Exception:
            return False
    
    def export(self, snapshot_id: str, export_path: str) -> bool:
        """导出快照到文件
        
        Args:
            snapshot_id: 快照ID
            export_path: 导出路径
            
        Returns:
            是否导出成功
        """
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if not state_file.exists():
            return False
        
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建包含元数据的导出文件
            export_data = {
                'snapshot': snapshot.to_dict(),
                'exported_at': datetime.now().isoformat()
            }
            
            import tarfile
            with tarfile.open(export_file, 'w:gz') as tar:
                # 添加状态数据
                tar.add(state_file, arcname='state.dat')
                
                # 添加元数据
                import io
                meta_bytes = json.dumps(export_data, ensure_ascii=False).encode()
                meta_info = tarfile.TarInfo(name='metadata.json')
                meta_info.size = len(meta_bytes)
                tar.addfile(meta_info, io.BytesIO(meta_bytes))
            
            return True
        except Exception as e:
            print(f"Failed to export snapshot: {e}")
            return False
    
    def import_snapshot(self, import_path: str) -> Optional[Snapshot]:
        """从文件导入快照
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            导入的快照对象
        """
        try:
            import tarfile
            import io
            
            with tarfile.open(import_path, 'r:gz') as tar:
                # 读取元数据
                meta_file = tar.extractfile('metadata.json')
                if not meta_file:
                    return None
                
                meta_data = json.loads(meta_file.read().decode())
                snapshot = Snapshot.from_dict(meta_data['snapshot'])
                
                # 读取状态数据
                state_file = tar.extractfile('state.dat')
                if not state_file:
                    return None
                
                state_data = state_file.read()
                
                # 保存到存储
                target_file = self._state_dir / f"{snapshot.id}.dat"
                with open(target_file, 'wb') as f:
                    f.write(state_data)
                
                # 更新索引
                self._snapshots[snapshot.id] = snapshot
                self._save_index()
                
                return snapshot
        except Exception as e:
            print(f"Failed to import snapshot: {e}")
            return None
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_size = 0
        for snapshot_id in self._snapshots:
            state_file = self._state_dir / f"{snapshot_id}.dat"
            if state_file.exists():
                total_size += state_file.stat().st_size
        
        return {
            'count': len(self._snapshots),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
