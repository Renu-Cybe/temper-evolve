#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持久化系统 (Persistence System) - 复利原则

本模块实现状态持久化机制，支持：
1. 状态持久化：保存和恢复系统状态
2. 增量保存：支持增量更新
3. 版本迁移：支持数据版本迁移
4. 数据完整性：确保数据不损坏

编码规范（Codong风格）：
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 提取成功值
- 使用 is_error() 检查错误
"""

import json
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from contextlib import contextmanager
import tempfile

# Windows 兼容性：fcntl 仅在 Unix 上可用
try:
    import fcntl
except ImportError:
    fcntl = None

# ============================================================================
# 工具函数
# ============================================================================

def is_error(result: Dict[str, Any]) -> bool:
    """检查结果是否为错误"""
    return not result.get("ok", False)


def unwrap(result: Dict[str, Any]) -> Any:
    """从结果中提取值，如果是错误则抛出异常"""
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def success(value: Any = None) -> Dict[str, Any]:
    """创建成功结果"""
    return {"ok": True, "value": value}


def failure(error: str, message: str) -> Dict[str, Any]:
    """创建失败结果"""
    return {"ok": False, "error": error, "message": message}


def compute_hash(data: bytes) -> str:
    """计算数据的SHA256哈希值"""
    return hashlib.sha256(data).hexdigest()


def atomic_write(filepath: Path, data: bytes) -> Dict[str, Any]:
    """
    原子写入文件
    
    使用临时文件 + 重命名确保写入的原子性
    """
    try:
        # 确保目录存在
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent,
            prefix=f".{filepath.name}.tmp."
        )
        
        try:
            os.write(fd, data)
            os.fsync(fd)  # 确保数据写入磁盘
        finally:
            os.close(fd)
        
        # 原子重命名
        os.rename(temp_path, filepath)
        
        # 同步目录
        dir_fd = os.open(filepath.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        
        return success()
    except Exception as e:
        # 清理临时文件
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        return failure("WRITE_ERROR", f"原子写入失败: {str(e)}")


# ============================================================================
# 快照类 (Snapshot)
# ============================================================================

@dataclass
class SnapshotMetadata:
    """快照元数据"""
    id: str                    # 快照ID
    timestamp: float           # 创建时间戳
    version: int               # 数据版本
    parent_id: Optional[str]   # 父快照ID（增量快照用）
    checksum: str              # 数据校验和
    size: int                  # 数据大小
    description: str           # 描述
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotMetadata":
        """从字典创建"""
        return cls(**data)


class Snapshot:
    """
    快照管理类
    
    负责创建、加载和管理数据快照，支持：
    - 完整快照
    - 增量快照
    - 快照链管理
    """
    
    def __init__(self, snapshot_dir: Path):
        """
        初始化快照管理器
        
        Args:
            snapshot_dir: 快照存储目录
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.metadata_dir = self.snapshot_dir / "metadata"
        self.data_dir = self.snapshot_dir / "data"
        
        # 确保目录存在
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_id(self) -> str:
        """生成唯一快照ID"""
        timestamp = time.time()
        random_bytes = os.urandom(16)
        return compute_hash(f"{timestamp}{random_bytes.hex()}".encode())[:16]
    
    def _get_metadata_path(self, snapshot_id: str) -> Path:
        """获取元数据文件路径"""
        return self.metadata_dir / f"{snapshot_id}.json"
    
    def _get_data_path(self, snapshot_id: str) -> Path:
        """获取数据文件路径"""
        return self.data_dir / f"{snapshot_id}.dat"
    
    def create(
        self,
        data: Dict[str, Any],
        version: int = 1,
        parent_id: Optional[str] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建新快照
        
        Args:
            data: 要保存的数据
            version: 数据版本
            parent_id: 父快照ID（增量快照）
            description: 快照描述
            
        Returns:
            {"ok": True, "value": snapshot_id} 或错误
        """
        try:
            # 生成快照ID
            snapshot_id = self._generate_id()
            
            # 序列化数据
            if parent_id:
                # 增量快照：只保存差异
                parent_data_result = self._load_data(parent_id)
                if is_error(parent_data_result):
                    return parent_data_result
                parent_data = unwrap(parent_data_result)
                diff_data = self._compute_diff(parent_data, data)
                data_to_save = {"_diff": True, "parent": parent_id, "changes": diff_data}
            else:
                # 完整快照
                data_to_save = data
            
            # 序列化并计算校验和
            serialized = json.dumps(data_to_save, ensure_ascii=False, sort_keys=True).encode('utf-8')
            checksum = compute_hash(serialized)
            
            # 保存数据
            data_path = self._get_data_path(snapshot_id)
            result = atomic_write(data_path, serialized)
            if is_error(result):
                return result
            
            # 创建元数据
            metadata = SnapshotMetadata(
                id=snapshot_id,
                timestamp=time.time(),
                version=version,
                parent_id=parent_id,
                checksum=checksum,
                size=len(serialized),
                description=description
            )
            
            # 保存元数据
            metadata_path = self._get_metadata_path(snapshot_id)
            metadata_bytes = json.dumps(metadata.to_dict(), ensure_ascii=False).encode('utf-8')
            result = atomic_write(metadata_path, metadata_bytes)
            if is_error(result):
                # 清理已保存的数据
                try:
                    data_path.unlink()
                except:
                    pass
                return result
            
            return success(snapshot_id)
            
        except Exception as e:
            return failure("SNAPSHOT_CREATE_ERROR", f"创建快照失败: {str(e)}")
    
    def _compute_diff(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算两个字典的差异
        
        Returns:
            包含 added, modified, removed 的差异字典
        """
        diff = {"added": {}, "modified": {}, "removed": []}
        
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        # 新增的键
        for key in new_keys - old_keys:
            diff["added"][key] = new_data[key]
        
        # 删除的键
        for key in old_keys - new_keys:
            diff["removed"].append(key)
        
        # 修改的键
        for key in old_keys & new_keys:
            if old_data[key] != new_data[key]:
                diff["modified"][key] = new_data[key]
        
        return diff
    
    def _apply_diff(
        self,
        base_data: Dict[str, Any],
        diff: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将差异应用到基础数据"""
        result = dict(base_data)
        
        # 应用新增
        result.update(diff.get("added", {}))
        
        # 应用修改
        result.update(diff.get("modified", {}))
        
        # 应用删除
        for key in diff.get("removed", []):
            result.pop(key, None)
        
        return result
    
    def load(self, snapshot_id: str) -> Dict[str, Any]:
        """
        加载快照
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            {"ok": True, "value": (metadata, data)} 或错误
        """
        try:
            # 加载元数据
            metadata_result = self._load_metadata(snapshot_id)
            if is_error(metadata_result):
                return metadata_result
            metadata = unwrap(metadata_result)
            
            # 加载数据
            data_result = self._load_data(snapshot_id)
            if is_error(data_result):
                return data_result
            data = unwrap(data_result)
            
            return success((metadata, data))
            
        except Exception as e:
            return failure("SNAPSHOT_LOAD_ERROR", f"加载快照失败: {str(e)}")
    
    def _load_metadata(self, snapshot_id: str) -> Dict[str, Any]:
        """加载快照元数据"""
        metadata_path = self._get_metadata_path(snapshot_id)
        
        if not metadata_path.exists():
            return failure("SNAPSHOT_NOT_FOUND", f"快照不存在: {snapshot_id}")
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return success(SnapshotMetadata.from_dict(data))
        except Exception as e:
            return failure("METADATA_READ_ERROR", f"读取元数据失败: {str(e)}")
    
    def _load_data(self, snapshot_id: str) -> Dict[str, Any]:
        """加载快照数据"""
        # 首先加载元数据
        metadata_result = self._load_metadata(snapshot_id)
        if is_error(metadata_result):
            return metadata_result
        metadata = unwrap(metadata_result)
        
        data_path = self._get_data_path(snapshot_id)
        
        if not data_path.exists():
            return failure("DATA_NOT_FOUND", f"快照数据不存在: {snapshot_id}")
        
        try:
            with open(data_path, 'rb') as f:
                serialized = f.read()
            
            # 验证校验和
            actual_checksum = compute_hash(serialized)
            if actual_checksum != metadata.checksum:
                return failure(
                    "CHECKSUM_MISMATCH",
                    f"数据校验失败: 期望 {metadata.checksum}, 实际 {actual_checksum}"
                )
            
            data = json.loads(serialized.decode('utf-8'))
            
            # 如果是增量快照，需要重建完整数据
            if data.get("_diff"):
                parent_id = data["parent"]
                parent_data_result = self._load_data(parent_id)
                if is_error(parent_data_result):
                    return failure(
                        "DIFF_RESOLVE_ERROR",
                        f"无法加载父快照 {parent_id}: {parent_data_result.get('message')}"
                    )
                parent_data = unwrap(parent_data_result)
                data = self._apply_diff(parent_data, data["changes"])
            
            return success(data)
            
        except Exception as e:
            return failure("DATA_READ_ERROR", f"读取数据失败: {str(e)}")
    
    def list_snapshots(self) -> Dict[str, Any]:
        """
        列出所有快照
        
        Returns:
            {"ok": True, "value": [SnapshotMetadata, ...]} 或错误
        """
        try:
            snapshots = []
            for metadata_file in self.metadata_dir.glob("*.json"):
                snapshot_id = metadata_file.stem
                result = self._load_metadata(snapshot_id)
                if not is_error(result):
                    snapshots.append(unwrap(result))
            
            # 按时间戳排序
            snapshots.sort(key=lambda x: x.timestamp, reverse=True)
            return success(snapshots)
            
        except Exception as e:
            return failure("LIST_ERROR", f"列出快照失败: {str(e)}")
    
    def delete(self, snapshot_id: str) -> Dict[str, Any]:
        """
        删除快照
        
        Args:
            snapshot_id: 要删除的快照ID
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            # 检查是否有子快照依赖此快照
            snapshots_result = self.list_snapshots()
            if is_error(snapshots_result):
                return snapshots_result
            
            snapshots = unwrap(snapshots_result)
            for snap in snapshots:
                if snap.parent_id == snapshot_id:
                    return failure(
                        "DEPENDENCY_ERROR",
                        f"无法删除: 快照 {snap.id} 依赖于此快照"
                    )
            
            # 删除元数据和数据文件
            metadata_path = self._get_metadata_path(snapshot_id)
            data_path = self._get_data_path(snapshot_id)
            
            if metadata_path.exists():
                metadata_path.unlink()
            
            if data_path.exists():
                data_path.unlink()
            
            return success()
            
        except Exception as e:
            return failure("DELETE_ERROR", f"删除快照失败: {str(e)}")
    
    def cleanup_orphaned(self) -> Dict[str, Any]:
        """
        清理孤立的快照文件
        
        Returns:
            {"ok": True, "value": 清理的文件数} 或错误
        """
        try:
            # 获取所有有效的快照ID
            snapshots_result = self.list_snapshots()
            if is_error(snapshots_result):
                return snapshots_result
            
            valid_ids = {snap.id for snap in unwrap(snapshots_result)}
            
            cleaned = 0
            
            # 清理孤立的数据文件
            for data_file in self.data_dir.glob("*.dat"):
                snapshot_id = data_file.stem
                if snapshot_id not in valid_ids:
                    data_file.unlink()
                    cleaned += 1
            
            return success(cleaned)
            
        except Exception as e:
            return failure("CLEANUP_ERROR", f"清理失败: {str(e)}")


# ============================================================================
# 迁移类 (Migration)
# ============================================================================

@dataclass
class MigrationRecord:
    """迁移记录"""
    version_from: int          # 起始版本
    version_to: int            # 目标版本
    timestamp: float           # 迁移时间
    success: bool              # 是否成功
    message: str               # 迁移信息


class Migration:
    """
    版本迁移管理类
    
    负责管理数据版本迁移，支持：
    - 注册迁移函数
    - 执行版本升级/降级
    - 迁移历史记录
    """
    
    def __init__(self, migration_dir: Path):
        """
        初始化迁移管理器
        
        Args:
            migration_dir: 迁移记录存储目录
        """
        self.migration_dir = Path(migration_dir)
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        
        self._up_migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._down_migrations: Dict[int, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        
        self._history_file = self.migration_dir / "history.json"
    
    def register(
        self,
        version: int,
        up_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        down_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        注册迁移函数
        
        Args:
            version: 目标版本号（从version-1升级到version）
            up_func: 升级函数
            down_func: 降级函数（可选）
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            self._up_migrations[version] = up_func
            if down_func:
                self._down_migrations[version] = down_func
            return success()
        except Exception as e:
            return failure("REGISTER_ERROR", f"注册迁移失败: {str(e)}")
    
    def migrate(
        self,
        data: Dict[str, Any],
        current_version: int,
        target_version: int
    ) -> Dict[str, Any]:
        """
        执行数据迁移
        
        Args:
            data: 要迁移的数据
            current_version: 当前版本
            target_version: 目标版本
            
        Returns:
            {"ok": True, "value": (new_data, new_version)} 或错误
        """
        try:
            if current_version == target_version:
                return success((data, current_version))
            
            if current_version < target_version:
                # 升级
                for version in range(current_version + 1, target_version + 1):
                    if version not in self._up_migrations:
                        return failure(
                            "MIGRATION_NOT_FOUND",
                            f"找不到版本 {version} 的升级迁移"
                        )
                    
                    migrate_func = self._up_migrations[version]
                    data = migrate_func(data)
                    
                    # 记录迁移
                    self._record_migration(version - 1, version, True, "升级成功")
                
                return success((data, target_version))
            
            else:
                # 降级
                for version in range(current_version, target_version, -1):
                    if version not in self._down_migrations:
                        return failure(
                            "MIGRATION_NOT_FOUND",
                            f"找不到版本 {version} 的降级迁移"
                        )
                    
                    migrate_func = self._down_migrations[version]
                    data = migrate_func(data)
                    
                    # 记录迁移
                    self._record_migration(version, version - 1, True, "降级成功")
                
                return success((data, target_version))
                
        except Exception as e:
            self._record_migration(current_version, target_version, False, str(e))
            return failure("MIGRATE_ERROR", f"迁移失败: {str(e)}")
    
    def _record_migration(
        self,
        version_from: int,
        version_to: int,
        success: bool,
        message: str
    ) -> None:
        """记录迁移历史"""
        try:
            record = MigrationRecord(
                version_from=version_from,
                version_to=version_to,
                timestamp=time.time(),
                success=success,
                message=message
            )
            
            history = []
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            history.append(asdict(record))
            
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception:
            pass  # 记录失败不影响主流程
    
    def get_history(self) -> Dict[str, Any]:
        """
        获取迁移历史
        
        Returns:
            {"ok": True, "value": [MigrationRecord, ...]} 或错误
        """
        try:
            if not self._history_file.exists():
                return success([])
            
            with open(self._history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            records = [MigrationRecord(**item) for item in history]
            return success(records)
            
        except Exception as e:
            return failure("HISTORY_ERROR", f"获取迁移历史失败: {str(e)}")
    
    def get_available_versions(self) -> Dict[str, Any]:
        """
        获取可用的迁移版本
        
        Returns:
            {"ok": True, "value": {"up": [...], "down": [...]}} 或错误
        """
        return success({
            "up": sorted(self._up_migrations.keys()),
            "down": sorted(self._down_migrations.keys())
        })


# ============================================================================
# 状态管理器 (StateManager)
# ============================================================================

class StateManager:
    """
    状态管理器
    
    负责管理系统状态的持久化，提供：
    - 状态保存和加载
    - 自动快照
    - 增量更新
    - 版本控制
    """
    
    def __init__(
        self,
        name: str,
        data_dir: Optional[Path] = None,
        auto_snapshot: bool = True,
        max_snapshots: int = 10
    ):
        """
        初始化状态管理器
        
        Args:
            name: 状态管理器名称
            data_dir: 数据目录（默认为 ~/.temper/data/）
            auto_snapshot: 是否自动创建快照
            max_snapshots: 最大快照数量
        """
        self.name = name
        self.auto_snapshot = auto_snapshot
        self.max_snapshots = max_snapshots
        
        # 设置数据目录
        if data_dir is None:
            home = Path.home()
            data_dir = home / ".temper" / "data"
        
        self.base_dir = Path(data_dir) / name
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.snapshot = Snapshot(self.base_dir / "snapshots")
        self.migration = Migration(self.base_dir / "migrations")
        
        # 状态文件
        self.state_file = self.base_dir / "state.json"
        self.version_file = self.base_dir / "version"
        
        # 当前状态
        self._state: Dict[str, Any] = {}
        self._version: int = 1
        self._dirty: bool = False
        
        # 锁文件
        self._lock_file: Optional[int] = None
        
        # 加载现有状态
        self._load_state()
    
    def _load_state(self) -> None:
        """加载现有状态"""
        try:
            # 加载版本
            if self.version_file.exists():
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    self._version = int(f.read().strip())
            
            # 加载状态
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
        except Exception:
            self._state = {}
            self._version = 1
    
    def _acquire_lock(self) -> Dict[str, Any]:
        """获取文件锁"""
        try:
            lock_path = self.base_dir / ".lock"
            self._lock_file = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
            if fcntl:
                fcntl.flock(self._lock_file, fcntl.LOCK_EX)
            return success()
        except Exception as e:
            return failure("LOCK_ERROR", f"获取锁失败: {str(e)}")
    
    def _release_lock(self) -> None:
        """释放文件锁"""
        if self._lock_file is not None:
            try:
                if fcntl:
                    fcntl.flock(self._lock_file, fcntl.LOCK_UN)
                os.close(self._lock_file)
                self._lock_file = None
            except:
                pass
    
    @contextmanager
    def _locked(self):
        """锁上下文管理器"""
        result = self._acquire_lock()
        if is_error(result):
            raise RuntimeError(unwrap(result))
        try:
            yield
        finally:
            self._release_lock()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取状态值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            状态值或默认值
        """
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> Dict[str, Any]:
        """
        设置状态值
        
        Args:
            key: 键名
            value: 值
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            self._state[key] = value
            self._dirty = True
            return success()
        except Exception as e:
            return failure("SET_ERROR", f"设置状态失败: {str(e)}")
    
    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量更新状态
        
        Args:
            updates: 更新字典
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            self._state.update(updates)
            self._dirty = True
            return success()
        except Exception as e:
            return failure("UPDATE_ERROR", f"更新状态失败: {str(e)}")
    
    def delete(self, key: str) -> Dict[str, Any]:
        """
        删除状态值
        
        Args:
            key: 键名
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            if key in self._state:
                del self._state[key]
                self._dirty = True
            return success()
        except Exception as e:
            return failure("DELETE_ERROR", f"删除状态失败: {str(e)}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有状态
        
        Returns:
            {"ok": True, "value": 状态字典} 或错误
        """
        return success(dict(self._state))
    
    def save(self, description: str = "") -> Dict[str, Any]:
        """
        保存状态
        
        Args:
            description: 保存描述
            
        Returns:
            {"ok": True, "value": snapshot_id} 或错误
        """
        try:
            with self._locked():
                # 序列化状态
                serialized = json.dumps(self._state, ensure_ascii=False, sort_keys=True).encode('utf-8')
                
                # 原子写入状态文件
                result = atomic_write(self.state_file, serialized)
                if is_error(result):
                    return result
                
                # 写入版本
                result = atomic_write(self.version_file, str(self._version).encode('utf-8'))
                if is_error(result):
                    return result
                
                self._dirty = False
                
                # 创建快照
                snapshot_id = None
                if self.auto_snapshot:
                    # 获取最后一个快照作为父快照
                    snapshots_result = self.snapshot.list_snapshots()
                    parent_id = None
                    if not is_error(snapshots_result):
                        snapshots = unwrap(snapshots_result)
                        if snapshots:
                            parent_id = snapshots[0].id
                    
                    result = self.snapshot.create(
                        self._state,
                        version=self._version,
                        parent_id=parent_id,
                        description=description or f"Auto save at {datetime.now().isoformat()}"
                    )
                    if not is_error(result):
                        snapshot_id = unwrap(result)
                        
                        # 清理旧快照
                        self._cleanup_old_snapshots()
                
                return success(snapshot_id)
                
        except Exception as e:
            return failure("SAVE_ERROR", f"保存状态失败: {str(e)}")
    
    def _cleanup_old_snapshots(self) -> None:
        """清理旧快照"""
        try:
            snapshots_result = self.snapshot.list_snapshots()
            if is_error(snapshots_result):
                return
            
            snapshots = unwrap(snapshots_result)
            if len(snapshots) > self.max_snapshots:
                # 保留最近的快照，删除旧的
                to_delete = snapshots[self.max_snapshots:]
                for snap in to_delete:
                    self.snapshot.delete(snap.id)
        except Exception:
            pass
    
    def load(self) -> Dict[str, Any]:
        """
        从文件加载状态
        
        Returns:
            {"ok": True, "value": 状态字典} 或错误
        """
        try:
            with self._locked():
                self._load_state()
                return success(dict(self._state))
        except Exception as e:
            return failure("LOAD_ERROR", f"加载状态失败: {str(e)}")
    
    def restore(self, snapshot_id: str) -> Dict[str, Any]:
        """
        从快照恢复状态
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            {"ok": True} 或错误
        """
        try:
            with self._locked():
                result = self.snapshot.load(snapshot_id)
                if is_error(result):
                    return result
                
                metadata, data = unwrap(result)
                self._state = data
                self._version = metadata.version
                self._dirty = True
                
                # 保存恢复后的状态
                return self.save(f"Restored from snapshot {snapshot_id}")
                
        except Exception as e:
            return failure("RESTORE_ERROR", f"恢复快照失败: {str(e)}")
    
    def migrate_to(self, target_version: int) -> Dict[str, Any]:
        """
        迁移到指定版本
        
        Args:
            target_version: 目标版本
            
        Returns:
            {"ok": True, "value": new_version} 或错误
        """
        try:
            with self._locked():
                result = self.migration.migrate(
                    self._state,
                    self._version,
                    target_version
                )
                if is_error(result):
                    return result
                
                new_data, new_version = unwrap(result)
                self._state = new_data
                self._version = new_version
                self._dirty = True
                
                # 保存迁移后的状态
                save_result = self.save(f"Migrated to version {new_version}")
                if is_error(save_result):
                    return save_result
                
                return success(new_version)
                
        except Exception as e:
            return failure("MIGRATE_ERROR", f"迁移失败: {str(e)}")
    
    def get_version(self) -> int:
        """获取当前版本"""
        return self._version
    
    def is_dirty(self) -> bool:
        """检查状态是否有未保存的更改"""
        return self._dirty
    
    def clear(self) -> Dict[str, Any]:
        """
        清空状态
        
        Returns:
            {"ok": True} 或错误
        """
        try:
            with self._locked():
                self._state = {}
                self._dirty = True
                
                # 删除状态文件
                if self.state_file.exists():
                    self.state_file.unlink()
                
                return success()
        except Exception as e:
            return failure("CLEAR_ERROR", f"清空状态失败: {str(e)}")
    
    def backup(self, backup_dir: Path) -> Dict[str, Any]:
        """
        备份状态到指定目录
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            {"ok": True, "value": 备份路径} 或错误
        """
        try:
            backup_path = Path(backup_dir) / f"{self.name}_backup_{int(time.time())}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 复制所有文件
            for item in self.base_dir.rglob("*"):
                if item.is_file():
                    relative = item.relative_to(self.base_dir)
                    dest = backup_path / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
            
            return success(backup_path)
            
        except Exception as e:
            return failure("BACKUP_ERROR", f"备份失败: {str(e)}")


# ============================================================================
# 全局持久化函数
# ============================================================================

# 全局状态管理器注册表
_state_managers: Dict[str, StateManager] = {}


def get_state_manager(name: str, **kwargs) -> StateManager:
    """
    获取或创建状态管理器
    
    Args:
        name: 状态管理器名称
        **kwargs: 传递给StateManager构造函数的参数
        
    Returns:
        StateManager实例
    """
    if name not in _state_managers:
        _state_managers[name] = StateManager(name, **kwargs)
    return _state_managers[name]


def remove_state_manager(name: str) -> Dict[str, Any]:
    """
    移除状态管理器
    
    Args:
        name: 状态管理器名称
        
    Returns:
        {"ok": True} 或错误
    """
    if name in _state_managers:
        del _state_managers[name]
    return success()


def list_state_managers() -> List[str]:
    """列出所有已注册的状态管理器"""
    return list(_state_managers.keys())


def persist_get(name: str, key: str, default: Any = None) -> Any:
    """
    从指定状态管理器获取值
    
    Args:
        name: 状态管理器名称
        key: 键名
        default: 默认值
        
    Returns:
        值或默认值
    """
    manager = get_state_manager(name)
    return manager.get(key, default)


def persist_set(name: str, key: str, value: Any) -> Dict[str, Any]:
    """
    向指定状态管理器设置值
    
    Args:
        name: 状态管理器名称
        key: 键名
        value: 值
        
    Returns:
        {"ok": True} 或错误
    """
    manager = get_state_manager(name)
    return manager.set(key, value)


def persist_save(name: str, description: str = "") -> Dict[str, Any]:
    """
    保存指定状态管理器的状态
    
    Args:
        name: 状态管理器名称
        description: 保存描述
        
    Returns:
        {"ok": True, "value": snapshot_id} 或错误
    """
    manager = get_state_manager(name)
    return manager.save(description)


def persist_load(name: str) -> Dict[str, Any]:
    """
    加载指定状态管理器的状态
    
    Args:
        name: 状态管理器名称
        
    Returns:
        {"ok": True, "value": 状态字典} 或错误
    """
    manager = get_state_manager(name)
    return manager.load()


def persist_restore(name: str, snapshot_id: str) -> Dict[str, Any]:
    """
    从快照恢复指定状态管理器的状态
    
    Args:
        name: 状态管理器名称
        snapshot_id: 快照ID
        
    Returns:
        {"ok": True} 或错误
    """
    manager = get_state_manager(name)
    return manager.restore(snapshot_id)


def persist_list_snapshots(name: str) -> Dict[str, Any]:
    """
    列出指定状态管理器的快照
    
    Args:
        name: 状态管理器名称
        
    Returns:
        {"ok": True, "value": [SnapshotMetadata, ...]} 或错误
    """
    manager = get_state_manager(name)
    return manager.snapshot.list_snapshots()


def persist_clear(name: str) -> Dict[str, Any]:
    """
    清空指定状态管理器的状态
    
    Args:
        name: 状态管理器名称
        
    Returns:
        {"ok": True} 或错误
    """
    manager = get_state_manager(name)
    return manager.clear()


def persist_backup(name: str, backup_dir: Path) -> Dict[str, Any]:
    """
    备份指定状态管理器的状态
    
    Args:
        name: 状态管理器名称
        backup_dir: 备份目录
        
    Returns:
        {"ok": True, "value": 备份路径} 或错误
    """
    manager = get_state_manager(name)
    return manager.backup(backup_dir)


# ============================================================================
# 便捷函数
# ============================================================================

def create_full_backup(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    创建完整备份
    
    Args:
        data_dir: 数据目录（默认为 ~/.temper/data/）
        
    Returns:
        {"ok": True, "value": 备份路径} 或错误
    """
    try:
        if data_dir is None:
            data_dir = Path.home() / ".temper" / "data"
        
        data_dir = Path(data_dir)
        
        if not data_dir.exists():
            return failure("DATA_DIR_NOT_FOUND", f"数据目录不存在: {data_dir}")
        
        # 创建备份目录
        backup_name = f"temper_backup_{int(time.time())}"
        backup_path = data_dir.parent / "backups" / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 复制整个数据目录
        for item in data_dir.rglob("*"):
            if item.is_file():
                relative = item.relative_to(data_dir)
                dest = backup_path / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
        
        return success(backup_path)
        
    except Exception as e:
        return failure("BACKUP_ERROR", f"创建备份失败: {str(e)}")


def restore_from_backup(backup_path: Path, data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    从备份恢复
    
    Args:
        backup_path: 备份路径
        data_dir: 数据目录（默认为 ~/.temper/data/）
        
    Returns:
        {"ok": True} 或错误
    """
    try:
        if data_dir is None:
            data_dir = Path.home() / ".temper" / "data"
        
        data_dir = Path(data_dir)
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return failure("BACKUP_NOT_FOUND", f"备份不存在: {backup_path}")
        
        # 如果数据目录存在，先备份当前状态
        if data_dir.exists():
            temp_backup = data_dir.parent / f"temp_backup_{int(time.time())}"
            shutil.move(str(data_dir), str(temp_backup))
        
        try:
            # 复制备份到数据目录
            shutil.copytree(backup_path, data_dir)
            
            # 删除临时备份
            if 'temp_backup' in locals():
                shutil.rmtree(temp_backup)
            
            return success()
            
        except Exception as e:
            # 恢复失败，尝试恢复原来的数据
            if 'temp_backup' in locals() and temp_backup.exists():
                if data_dir.exists():
                    shutil.rmtree(data_dir)
                shutil.move(str(temp_backup), str(data_dir))
            raise e
            
    except Exception as e:
        return failure("RESTORE_ERROR", f"恢复备份失败: {str(e)}")


# ============================================================================
# 模块测试
# ============================================================================

if __name__ == "__main__":
    # 简单测试
    print("=== 持久化系统测试 ===")
    
    # 测试状态管理器
    manager = StateManager("test", auto_snapshot=True, max_snapshots=5)
    
    # 设置一些值
    print("\n1. 设置状态值")
    result = manager.set("key1", "value1")
    print(f"   set key1: {result}")
    
    result = manager.set("key2", {"nested": "data"})
    print(f"   set key2: {result}")
    
    # 保存状态
    print("\n2. 保存状态")
    result = manager.save("Initial save")
    print(f"   save: {result}")
    snapshot_id = unwrap(result)
    print(f"   snapshot_id: {snapshot_id}")
    
    # 更新值
    print("\n3. 更新状态")
    result = manager.set("key1", "updated_value")
    print(f"   update key1: {result}")
    
    # 再次保存
    print("\n4. 再次保存")
    result = manager.save("Second save")
    print(f"   save: {result}")
    
    # 列出快照
    print("\n5. 列出快照")
    result = manager.snapshot.list_snapshots()
    print(f"   list_snapshots: {result}")
    
    # 获取值
    print("\n6. 获取值")
    print(f"   key1: {manager.get('key1')}")
    print(f"   key2: {manager.get('key2')}")
    
    # 测试全局函数
    print("\n7. 测试全局函数")
    result = persist_set("global_test", "test_key", "test_value")
    print(f"   persist_set: {result}")
    
    result = persist_save("global_test", "Global test save")
    print(f"   persist_save: {result}")
    
    value = persist_get("global_test", "test_key")
    print(f"   persist_get: {value}")
    
    # 清理
    print("\n8. 清理")
    manager.clear()
    remove_state_manager("global_test")
    
    print("\n=== 测试完成 ===")
