#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Temper 审计系统 - 信任原则实现

功能：
1. 审计日志：记录所有关键操作
2. 操作回溯：支持操作历史查询
3. 备份管理：修改前自动创建备份
4. 回滚支持：支持操作回滚

编码规范（Codong风格）：
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 提取成功值
- 使用 is_error() 检查错误
"""

import os
import json
import hashlib
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from functools import wraps
from contextlib import contextmanager


# =============================================================================
# Codong 风格错误处理工具函数
# =============================================================================

def is_error(result: Dict[str, Any]) -> bool:
    """
    检查操作结果是否为错误
    
    Args:
        result: 操作返回的结果字典
        
    Returns:
        True 如果是错误，False 如果成功
    """
    if not isinstance(result, dict):
        return True
    return not result.get("ok", False)


def unwrap(result: Dict[str, Any]) -> Any:
    """
    从操作结果中提取值，如果是错误则抛出异常
    
    Args:
        result: 操作返回的结果字典
        
    Returns:
        成功时的 value 值
        
    Raises:
        RuntimeError: 如果结果是错误
    """
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def success(value: Any = None) -> Dict[str, Any]:
    """
    创建成功响应
    
    Args:
        value: 返回值
        
    Returns:
        成功响应字典
    """
    return {"ok": True, "value": value}


def failure(error: str, message: str) -> Dict[str, Any]:
    """
    创建失败响应
    
    Args:
        error: 错误代码
        message: 错误消息
        
    Returns:
        失败响应字典
    """
    return {"ok": False, "error": error, "message": message}


# =============================================================================
# 审计日志系统
# =============================================================================

class AuditLogger:
    """
    审计日志管理器
    
    负责记录所有关键操作，确保日志不可篡改
    使用哈希链技术保证日志完整性
    """
    
    # 操作类型常量
    OP_FILE_CREATE = "FILE_CREATE"
    OP_FILE_MODIFY = "FILE_MODIFY"
    OP_FILE_DELETE = "FILE_DELETE"
    OP_FILE_READ = "FILE_READ"
    OP_BACKUP_CREATE = "BACKUP_CREATE"
    OP_BACKUP_RESTORE = "BACKUP_RESTORE"
    OP_ROLLBACK = "ROLLBACK"
    OP_CONFIG_CHANGE = "CONFIG_CHANGE"
    OP_SYSTEM_INIT = "SYSTEM_INIT"
    OP_USER_ACTION = "USER_ACTION"
    
    # 严重程度级别
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_CRITICAL = "CRITICAL"
    
    def __init__(self, audit_dir: Optional[str] = None):
        """
        初始化审计日志管理器
        
        Args:
            audit_dir: 审计日志目录，默认为 ~/.temper/audit/
        """
        if audit_dir is None:
            audit_dir = os.path.expanduser("~/.temper/audit")
        
        self.audit_dir = Path(audit_dir)
        self.log_file = self.audit_dir / "audit.log"
        self.index_file = self.audit_dir / "index.json"
        self.hash_chain_file = self.audit_dir / "hash_chain.json"
        
        # 确保目录存在
        self._ensure_directory()
        
        # 初始化哈希链
        self._init_hash_chain()
    
    def _ensure_directory(self) -> None:
        """确保审计目录存在"""
        try:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"警告：无法创建审计目录: {e}")
    
    def _init_hash_chain(self) -> None:
        """初始化哈希链，用于保证日志完整性"""
        if not self.hash_chain_file.exists():
            initial_chain = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "last_hash": "0" * 64,  # 初始哈希值
                "entry_count": 0
            }
            try:
                with open(self.hash_chain_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_chain, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"警告：无法初始化哈希链: {e}")
    
    def _get_last_hash(self) -> str:
        """获取最后一个日志条目的哈希值"""
        try:
            if self.hash_chain_file.exists():
                with open(self.hash_chain_file, 'r', encoding='utf-8') as f:
                    chain = json.load(f)
                    return chain.get("last_hash", "0" * 64)
        except Exception:
            pass
        return "0" * 64
    
    def _update_hash_chain(self, entry_hash: str) -> Dict[str, Any]:
        """
        更新哈希链
        
        Args:
            entry_hash: 新日志条目的哈希值
            
        Returns:
            Codong风格的结果字典
        """
        try:
            chain = {"last_hash": "0" * 64, "entry_count": 0}
            
            if self.hash_chain_file.exists():
                with open(self.hash_chain_file, 'r', encoding='utf-8') as f:
                    chain = json.load(f)
            
            chain["last_hash"] = entry_hash
            chain["entry_count"] = chain.get("entry_count", 0) + 1
            chain["updated_at"] = datetime.now().isoformat()
            
            with open(self.hash_chain_file, 'w', encoding='utf-8') as f:
                json.dump(chain, f, indent=2, ensure_ascii=False)
            
            return success(True)
        except Exception as e:
            return failure("HASH_CHAIN_ERROR", f"更新哈希链失败: {str(e)}")
    
    def _calculate_hash(self, entry: Dict[str, Any]) -> str:
        """
        计算日志条目的哈希值
        
        Args:
            entry: 日志条目字典
            
        Returns:
            SHA-256 哈希值
        """
        # 包含前一个哈希值，形成哈希链
        last_hash = self._get_last_hash()
        
        # 创建要哈希的数据
        data = {
            "previous_hash": last_hash,
            "timestamp": entry.get("timestamp"),
            "operation": entry.get("operation"),
            "details": entry.get("details")
        }
        
        # 计算哈希
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    def log(self, 
            operation: str, 
            details: Dict[str, Any],
            level: str = LEVEL_INFO,
            user: Optional[str] = None) -> Dict[str, Any]:
        """
        记录审计日志
        
        Args:
            operation: 操作类型
            details: 操作详情
            level: 严重程度级别
            user: 操作用户
            
        Returns:
            Codong风格的结果字典
        """
        try:
            # 创建日志条目
            entry = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "level": level,
                "user": user or os.environ.get("USER", "unknown"),
                "details": details,
                "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
            }
            
            # 计算哈希值
            entry_hash = self._calculate_hash(entry)
            entry["hash"] = entry_hash
            
            # 追加写入日志文件
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
            # 更新哈希链
            result = self._update_hash_chain(entry_hash)
            if is_error(result):
                return result
            
            # 更新索引
            self._update_index(entry)
            
            return success(entry["id"])
            
        except Exception as e:
            return failure("LOG_ERROR", f"记录审计日志失败: {str(e)}")
    
    def _update_index(self, entry: Dict[str, Any]) -> None:
        """更新日志索引"""
        try:
            index = {"entries": [], "by_operation": {}, "by_date": {}}
            
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            
            # 添加到主索引
            index["entries"].append({
                "id": entry["id"],
                "timestamp": entry["timestamp"],
                "operation": entry["operation"],
                "level": entry["level"]
            })
            
            # 按操作类型索引
            op = entry["operation"]
            if op not in index["by_operation"]:
                index["by_operation"][op] = []
            index["by_operation"][op].append(entry["id"])
            
            # 按日期索引
            date = entry["timestamp"][:10]  # YYYY-MM-DD
            if date not in index["by_date"]:
                index["by_date"][date] = []
            index["by_date"][date].append(entry["id"])
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"警告：更新索引失败: {e}")
    
    def query(self, 
              operation: Optional[str] = None,
              start_time: Optional[str] = None,
              end_time: Optional[str] = None,
              level: Optional[str] = None,
              limit: int = 100) -> Dict[str, Any]:
        """
        查询审计日志
        
        Args:
            operation: 操作类型过滤
            start_time: 开始时间 (ISO格式)
            end_time: 结束时间 (ISO格式)
            level: 严重程度过滤
            limit: 返回条目数量限制
            
        Returns:
            Codong风格的结果字典，包含匹配的日志条目列表
        """
        try:
            if not self.log_file.exists():
                return success([])
            
            results = []
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        
                        # 应用过滤条件
                        if operation and entry.get("operation") != operation:
                            continue
                        if level and entry.get("level") != level:
                            continue
                        if start_time and entry.get("timestamp", "") < start_time:
                            continue
                        if end_time and entry.get("timestamp", "") > end_time:
                            continue
                        
                        results.append(entry)
                        
                        if len(results) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            # 按时间倒序排列
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return success(results)
            
        except Exception as e:
            return failure("QUERY_ERROR", f"查询审计日志失败: {str(e)}")
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        验证日志完整性
        
        检查哈希链是否完整，检测是否有篡改
        
        Returns:
            Codong风格的结果字典
        """
        try:
            if not self.log_file.exists():
                return success({"valid": True, "message": "日志文件不存在，视为有效"})
            
            previous_hash = "0" * 64
            invalid_entries = []
            entry_count = 0
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        entry_count += 1
                        
                        # 验证哈希值
                        stored_hash = entry.get("hash")
                        
                        # 重新计算哈希
                        data = {
                            "previous_hash": previous_hash,
                            "timestamp": entry.get("timestamp"),
                            "operation": entry.get("operation"),
                            "details": entry.get("details")
                        }
                        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
                        calculated_hash = hashlib.sha256(json_str.encode('utf-8')).hexdigest()
                        
                        if stored_hash != calculated_hash:
                            invalid_entries.append({
                                "line": line_num,
                                "id": entry.get("id"),
                                "stored_hash": stored_hash,
                                "calculated_hash": calculated_hash
                            })
                        
                        previous_hash = stored_hash
                        
                    except json.JSONDecodeError:
                        invalid_entries.append({
                            "line": line_num,
                            "error": "JSON解析错误"
                        })
            
            if invalid_entries:
                return success({
                    "valid": False,
                    "message": f"发现 {len(invalid_entries)} 个无效条目",
                    "invalid_entries": invalid_entries,
                    "total_entries": entry_count
                })
            
            return success({
                "valid": True,
                "message": f"所有 {entry_count} 个条目验证通过",
                "total_entries": entry_count
            })
            
        except Exception as e:
            return failure("VERIFY_ERROR", f"验证日志完整性失败: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取审计日志统计信息
        
        Returns:
            Codong风格的结果字典，包含统计信息
        """
        try:
            stats = {
                "total_entries": 0,
                "by_operation": {},
                "by_level": {},
                "date_range": {"first": None, "last": None}
            }
            
            if not self.log_file.exists():
                return success(stats)
            
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        stats["total_entries"] += 1
                        
                        # 按操作类型统计
                        op = entry.get("operation", "UNKNOWN")
                        stats["by_operation"][op] = stats["by_operation"].get(op, 0) + 1
                        
                        # 按级别统计
                        level = entry.get("level", "UNKNOWN")
                        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
                        
                        # 时间范围
                        timestamp = entry.get("timestamp")
                        if timestamp:
                            if stats["date_range"]["first"] is None or timestamp < stats["date_range"]["first"]:
                                stats["date_range"]["first"] = timestamp
                            if stats["date_range"]["last"] is None or timestamp > stats["date_range"]["last"]:
                                stats["date_range"]["last"] = timestamp
                                
                    except json.JSONDecodeError:
                        continue
            
            return success(stats)
            
        except Exception as e:
            return failure("STATS_ERROR", f"获取统计信息失败: {str(e)}")


# =============================================================================
# 备份管理系统
# =============================================================================

class BackupManager:
    """
    备份管理器
    
    负责在文件修改前创建备份，支持备份版本管理
    """
    
    def __init__(self, 
                 backup_dir: Optional[str] = None,
                 audit_logger: Optional[AuditLogger] = None):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录，默认为 ~/.temper/backups/
            audit_logger: 审计日志管理器实例
        """
        if backup_dir is None:
            backup_dir = os.path.expanduser("~/.temper/backups")
        
        self.backup_dir = Path(backup_dir)
        self.metadata_file = self.backup_dir / "metadata.json"
        self.audit_logger = audit_logger
        
        # 确保目录存在
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """确保备份目录存在"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"警告：无法创建备份目录: {e}")
    
    def _generate_backup_id(self, original_path: str) -> str:
        """
        生成备份ID
        
        Args:
            original_path: 原始文件路径
            
        Returns:
            备份ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = Path(original_path).name
        return f"{timestamp}_{unique_id}_{filename}"
    
    def create_backup(self, 
                      file_path: str,
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            metadata: 额外的元数据
            
        Returns:
            Codong风格的结果字典，包含备份信息
        """
        try:
            source_path = Path(file_path)
            
            # 检查源文件是否存在
            if not source_path.exists():
                return failure("FILE_NOT_FOUND", f"文件不存在: {file_path}")
            
            # 生成备份ID和路径
            backup_id = self._generate_backup_id(file_path)
            backup_path = self.backup_dir / backup_id
            
            # 复制文件
            if source_path.is_file():
                shutil.copy2(source_path, backup_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, backup_path)
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(source_path)
            
            # 创建备份元数据
            backup_info = {
                "backup_id": backup_id,
                "original_path": str(source_path.absolute()),
                "backup_path": str(backup_path.absolute()),
                "created_at": datetime.now().isoformat(),
                "file_hash": file_hash,
                "is_directory": source_path.is_dir(),
                "size": self._get_size(source_path),
                "metadata": metadata or {}
            }
            
            # 保存元数据
            self._save_backup_metadata(backup_id, backup_info)
            
            # 记录审计日志
            if self.audit_logger:
                self.audit_logger.log(
                    operation=AuditLogger.OP_BACKUP_CREATE,
                    details={
                        "backup_id": backup_id,
                        "original_path": str(source_path),
                        "file_hash": file_hash
                    }
                )
            
            return success(backup_info)
            
        except Exception as e:
            return failure("BACKUP_ERROR", f"创建备份失败: {str(e)}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            
        Returns:
            SHA-256 哈希值
        """
        if file_path.is_dir():
            # 对于目录，计算所有文件的哈希组合
            hashes = []
            for f in sorted(file_path.rglob("*")):
                if f.is_file():
                    hashes.append(self._hash_single_file(f))
            return hashlib.sha256("".join(hashes).encode()).hexdigest()
        else:
            return self._hash_single_file(file_path)
    
    def _hash_single_file(self, file_path: Path) -> str:
        """计算单个文件的哈希值"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_size(self, path: Path) -> int:
        """获取文件或目录大小"""
        if path.is_file():
            return path.stat().st_size
        else:
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total
    
    def _save_backup_metadata(self, backup_id: str, info: Dict[str, Any]) -> None:
        """保存备份元数据"""
        try:
            metadata = {}
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            metadata[backup_id] = info
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"警告：保存备份元数据失败: {e}")
    
    def list_backups(self, 
                     original_path: Optional[str] = None,
                     limit: int = 100) -> Dict[str, Any]:
        """
        列出备份
        
        Args:
            original_path: 按原始路径过滤
            limit: 返回数量限制
            
        Returns:
            Codong风格的结果字典，包含备份列表
        """
        try:
            if not self.metadata_file.exists():
                return success([])
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            backups = []
            for backup_id, info in metadata.items():
                if original_path is None or info.get("original_path") == original_path:
                    backups.append(info)
            
            # 按创建时间倒序排列
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return success(backups[:limit])
            
        except Exception as e:
            return failure("LIST_ERROR", f"列出备份失败: {str(e)}")
    
    def get_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        获取备份信息
        
        Args:
            backup_id: 备份ID
            
        Returns:
            Codong风格的结果字典，包含备份信息
        """
        try:
            if not self.metadata_file.exists():
                return failure("NOT_FOUND", "备份不存在")
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if backup_id not in metadata:
                return failure("NOT_FOUND", f"备份不存在: {backup_id}")
            
            return success(metadata[backup_id])
            
        except Exception as e:
            return failure("GET_ERROR", f"获取备份信息失败: {str(e)}")
    
    def restore_backup(self, 
                       backup_id: str,
                       target_path: Optional[str] = None) -> Dict[str, Any]:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID
            target_path: 恢复目标路径，默认恢复到原始路径
            
        Returns:
            Codong风格的结果字典
        """
        try:
            # 获取备份信息
            result = self.get_backup(backup_id)
            if is_error(result):
                return result
            
            backup_info = unwrap(result)
            backup_path = Path(backup_info["backup_path"])
            
            if not backup_path.exists():
                return failure("BACKUP_MISSING", f"备份文件不存在: {backup_path}")
            
            # 确定目标路径
            if target_path is None:
                target_path = backup_info["original_path"]
            
            target = Path(target_path)
            
            # 如果目标存在，先备份当前状态
            if target.exists():
                current_backup = self.create_backup(
                    str(target),
                    metadata={"reason": "auto_backup_before_restore"}
                )
                if is_error(current_backup):
                    return failure("PRE_RESTORE_BACKUP_FAILED", 
                                 "恢复前自动备份失败")
            
            # 恢复文件
            if backup_info.get("is_directory"):
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(backup_path, target)
            else:
                shutil.copy2(backup_path, target)
            
            # 验证恢复的文件哈希
            restored_hash = self._calculate_file_hash(target)
            if restored_hash != backup_info.get("file_hash"):
                return failure("HASH_MISMATCH", 
                             "恢复后的文件哈希与备份不匹配")
            
            # 记录审计日志
            if self.audit_logger:
                self.audit_logger.log(
                    operation=AuditLogger.OP_BACKUP_RESTORE,
                    details={
                        "backup_id": backup_id,
                        "restored_to": str(target),
                        "hash_verified": True
                    }
                )
            
            return success({
                "backup_id": backup_id,
                "restored_to": str(target),
                "hash": restored_hash
            })
            
        except Exception as e:
            return failure("RESTORE_ERROR", f"恢复备份失败: {str(e)}")
    
    def delete_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        删除备份
        
        Args:
            backup_id: 备份ID
            
        Returns:
            Codong风格的结果字典
        """
        try:
            # 获取备份信息
            result = self.get_backup(backup_id)
            if is_error(result):
                return result
            
            backup_info = unwrap(result)
            backup_path = Path(backup_info["backup_path"])
            
            # 删除备份文件
            if backup_path.exists():
                if backup_path.is_dir():
                    shutil.rmtree(backup_path)
                else:
                    backup_path.unlink()
            
            # 更新元数据
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            del metadata[backup_id]
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return success(True)
            
        except Exception as e:
            return failure("DELETE_ERROR", f"删除备份失败: {str(e)}")
    
    def cleanup_old_backups(self, 
                           max_age_days: int = 30,
                           max_count: Optional[int] = None) -> Dict[str, Any]:
        """
        清理旧备份
        
        Args:
            max_age_days: 最大保留天数
            max_count: 每个文件的最大备份数量
            
        Returns:
            Codong风格的结果字典
        """
        try:
            result = self.list_backups(limit=10000)
            if is_error(result):
                return result
            
            backups = unwrap(result)
            deleted_count = 0
            
            now = datetime.now()
            
            for backup in backups:
                created_at = datetime.fromisoformat(backup.get("created_at", ""))
                age_days = (now - created_at).days
                
                if age_days > max_age_days:
                    del_result = self.delete_backup(backup["backup_id"])
                    if not is_error(del_result):
                        deleted_count += 1
            
            return success({
                "deleted_count": deleted_count,
                "remaining_count": len(backups) - deleted_count
            })
            
        except Exception as e:
            return failure("CLEANUP_ERROR", f"清理旧备份失败: {str(e)}")


# =============================================================================
# 回滚管理系统
# =============================================================================

class RollbackManager:
    """
    回滚管理器
    
    支持操作的回滚，维护操作栈以便撤销
    """
    
    def __init__(self, 
                 backup_manager: BackupManager,
                 audit_logger: Optional[AuditLogger] = None):
        """
        初始化回滚管理器
        
        Args:
            backup_manager: 备份管理器实例
            audit_logger: 审计日志管理器实例
        """
        self.backup_manager = backup_manager
        self.audit_logger = audit_logger
        self.operation_stack: List[Dict[str, Any]] = []
        self.max_stack_size = 100
    
    def register_operation(self, 
                          operation_type: str,
                          file_path: str,
                          backup_id: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        注册可回滚操作
        
        Args:
            operation_type: 操作类型
            file_path: 操作的文件路径
            backup_id: 备份ID
            metadata: 额外元数据
            
        Returns:
            Codong风格的结果字典
        """
        try:
            operation = {
                "id": str(uuid.uuid4()),
                "type": operation_type,
                "file_path": file_path,
                "backup_id": backup_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self.operation_stack.append(operation)
            
            # 限制栈大小
            if len(self.operation_stack) > self.max_stack_size:
                self.operation_stack.pop(0)
            
            return success(operation["id"])
            
        except Exception as e:
            return failure("REGISTER_ERROR", f"注册操作失败: {str(e)}")
    
    def rollback(self, 
                 operation_id: Optional[str] = None,
                 steps: int = 1) -> Dict[str, Any]:
        """
        回滚操作
        
        Args:
            operation_id: 指定要回滚的操作ID，None则回滚最近的操作
            steps: 回滚步数
            
        Returns:
            Codong风格的结果字典
        """
        try:
            if not self.operation_stack:
                return failure("EMPTY_STACK", "没有可回滚的操作")
            
            rolled_back = []
            
            if operation_id:
                # 找到指定操作
                found = False
                for i, op in enumerate(self.operation_stack):
                    if op["id"] == operation_id:
                        found = True
                        # 回滚从该操作到栈顶的所有操作
                        for j in range(len(self.operation_stack) - 1, i - 1, -1):
                            result = self._rollback_single(self.operation_stack[j])
                            if is_error(result):
                                return failure("ROLLBACK_FAILED", 
                                             f"回滚失败: {unwrap(result)}")
                            rolled_back.append(self.operation_stack[j])
                        # 移除已回滚的操作
                        self.operation_stack = self.operation_stack[:i]
                        break
                
                if not found:
                    return failure("NOT_FOUND", f"操作不存在: {operation_id}")
            else:
                # 回滚最近的操作
                for _ in range(min(steps, len(self.operation_stack))):
                    op = self.operation_stack.pop()
                    result = self._rollback_single(op)
                    if is_error(result):
                        return failure("ROLLBACK_FAILED", 
                                     f"回滚失败: {unwrap(result)}")
                    rolled_back.append(op)
            
            # 记录审计日志
            if self.audit_logger:
                self.audit_logger.log(
                    operation=AuditLogger.OP_ROLLBACK,
                    details={
                        "rolled_back_count": len(rolled_back),
                        "operations": [op["id"] for op in rolled_back]
                    },
                    level=AuditLogger.LEVEL_WARNING
                )
            
            return success({
                "rolled_back_count": len(rolled_back),
                "operations": rolled_back
            })
            
        except Exception as e:
            return failure("ROLLBACK_ERROR", f"回滚操作失败: {str(e)}")
    
    def _rollback_single(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """
        回滚单个操作
        
        Args:
            operation: 操作信息
            
        Returns:
            Codong风格的结果字典
        """
        backup_id = operation.get("backup_id")
        file_path = operation.get("file_path")
        
        # 恢复备份
        result = self.backup_manager.restore_backup(backup_id, file_path)
        return result
    
    def get_operation_history(self, limit: int = 50) -> Dict[str, Any]:
        """
        获取操作历史
        
        Args:
            limit: 返回数量限制
            
        Returns:
            Codong风格的结果字典
        """
        try:
            history = list(reversed(self.operation_stack[-limit:]))
            return success(history)
        except Exception as e:
            return failure("HISTORY_ERROR", f"获取操作历史失败: {str(e)}")
    
    def clear_history(self) -> Dict[str, Any]:
        """
        清空操作历史
        
        Returns:
            Codong风格的结果字典
        """
        try:
            cleared_count = len(self.operation_stack)
            self.operation_stack.clear()
            return success({"cleared_count": cleared_count})
        except Exception as e:
            return failure("CLEAR_ERROR", f"清空历史失败: {str(e)}")


# =============================================================================
# 全局审计函数和装饰器
# =============================================================================

# 全局审计日志实例
_global_audit_logger: Optional[AuditLogger] = None
_global_backup_manager: Optional[BackupManager] = None
_global_rollback_manager: Optional[RollbackManager] = None


def init_audit_system(audit_dir: Optional[str] = None,
                     backup_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    初始化全局审计系统
    
    Args:
        audit_dir: 审计日志目录
        backup_dir: 备份目录
        
    Returns:
        Codong风格的结果字典
    """
    global _global_audit_logger, _global_backup_manager, _global_rollback_manager
    
    try:
        # 初始化审计日志管理器
        _global_audit_logger = AuditLogger(audit_dir)
        
        # 初始化备份管理器
        _global_backup_manager = BackupManager(backup_dir, _global_audit_logger)
        
        # 初始化回滚管理器
        _global_rollback_manager = RollbackManager(
            _global_backup_manager, 
            _global_audit_logger
        )
        
        # 记录系统初始化
        _global_audit_logger.log(
            operation=AuditLogger.OP_SYSTEM_INIT,
            details={
                "audit_dir": str(_global_audit_logger.audit_dir),
                "backup_dir": str(_global_backup_manager.backup_dir)
            }
        )
        
        return success({
            "audit_logger": _global_audit_logger,
            "backup_manager": _global_backup_manager,
            "rollback_manager": _global_rollback_manager
        })
        
    except Exception as e:
        return failure("INIT_ERROR", f"初始化审计系统失败: {str(e)}")


def get_audit_logger() -> Optional[AuditLogger]:
    """获取全局审计日志管理器"""
    return _global_audit_logger


def get_backup_manager() -> Optional[BackupManager]:
    """获取全局备份管理器"""
    return _global_backup_manager


def get_rollback_manager() -> Optional[RollbackManager]:
    """获取全局回滚管理器"""
    return _global_rollback_manager


def audited_operation(operation_type: str, 
                     create_backup: bool = True,
                     register_rollback: bool = True):
    """
    审计装饰器 - 自动记录操作并支持回滚
    
    Args:
        operation_type: 操作类型
        create_backup: 是否在操作前创建备份
        register_rollback: 是否注册到回滚管理器
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取文件路径（假设第一个参数是文件路径）
            file_path = args[0] if args else kwargs.get('file_path')
            
            backup_id = None
            
            # 创建备份
            if create_backup and file_path and _global_backup_manager:
                result = _global_backup_manager.create_backup(file_path)
                if not is_error(result):
                    backup_info = unwrap(result)
                    backup_id = backup_info["backup_id"]
            
            # 执行操作
            try:
                result = func(*args, **kwargs)
                success_flag = not (isinstance(result, dict) and not result.get("ok", True))
                
                # 记录审计日志
                if _global_audit_logger:
                    _global_audit_logger.log(
                        operation=operation_type,
                        details={
                            "function": func.__name__,
                            "file_path": file_path,
                            "backup_id": backup_id,
                            "success": success_flag,
                            "args_count": len(args),
                            "kwargs_keys": list(kwargs.keys())
                        },
                        level=AuditLogger.LEVEL_INFO if success_flag else AuditLogger.LEVEL_ERROR
                    )
                
                # 注册回滚
                if register_rollback and backup_id and _global_rollback_manager:
                    _global_rollback_manager.register_operation(
                        operation_type=operation_type,
                        file_path=str(file_path) if file_path else "",
                        backup_id=backup_id
                    )
                
                return result
                
            except Exception as e:
                # 记录失败日志
                if _global_audit_logger:
                    _global_audit_logger.log(
                        operation=operation_type,
                        details={
                            "function": func.__name__,
                            "file_path": file_path,
                            "error": str(e),
                            "backup_id": backup_id
                        },
                        level=AuditLogger.LEVEL_ERROR
                    )
                raise
        
        return wrapper
    return decorator


@contextmanager
def audited_context(operation_type: str, 
                   file_path: Optional[str] = None,
                   create_backup: bool = True):
    """
    审计上下文管理器
    
    Args:
        operation_type: 操作类型
        file_path: 文件路径
        create_backup: 是否创建备份
        
    Yields:
        包含备份信息的字典
    """
    context_info = {
        "operation_type": operation_type,
        "file_path": file_path,
        "backup_id": None,
        "start_time": datetime.now().isoformat()
    }
    
    backup_id = None
    
    # 创建备份
    if create_backup and file_path and _global_backup_manager:
        result = _global_backup_manager.create_backup(file_path)
        if not is_error(result):
            backup_info = unwrap(result)
            backup_id = backup_info["backup_id"]
            context_info["backup_id"] = backup_id
    
    try:
        yield context_info
        
        # 记录成功
        if _global_audit_logger:
            _global_audit_logger.log(
                operation=operation_type,
                details={
                    "file_path": file_path,
                    "backup_id": backup_id,
                    "success": True
                }
            )
        
        # 注册回滚
        if backup_id and _global_rollback_manager:
            _global_rollback_manager.register_operation(
                operation_type=operation_type,
                file_path=str(file_path) if file_path else "",
                backup_id=backup_id
            )
            
    except Exception as e:
        # 记录失败
        if _global_audit_logger:
            _global_audit_logger.log(
                operation=operation_type,
                details={
                    "file_path": file_path,
                    "backup_id": backup_id,
                    "success": False,
                    "error": str(e)
                },
                level=AuditLogger.LEVEL_ERROR
            )
        raise


def safe_file_write(file_path: str, 
                   content: str,
                   encoding: str = 'utf-8') -> Dict[str, Any]:
    """
    安全的文件写入 - 自动备份和审计
    
    Args:
        file_path: 文件路径
        content: 写入内容
        encoding: 编码
        
    Returns:
        Codong风格的结果字典
    """
    path = Path(file_path)
    
    # 创建备份（如果文件存在）
    backup_id = None
    if path.exists() and _global_backup_manager:
        result = _global_backup_manager.create_backup(file_path)
        if not is_error(result):
            backup_info = unwrap(result)
            backup_id = backup_info["backup_id"]
    
    try:
        # 写入文件
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # 记录审计日志
        if _global_audit_logger:
            _global_audit_logger.log(
                operation=AuditLogger.OP_FILE_MODIFY,
                details={
                    "file_path": str(path.absolute()),
                    "backup_id": backup_id,
                    "size": len(content.encode(encoding))
                }
            )
        
        # 注册回滚
        if backup_id and _global_rollback_manager:
            _global_rollback_manager.register_operation(
                operation_type=AuditLogger.OP_FILE_MODIFY,
                file_path=str(path.absolute()),
                backup_id=backup_id
            )
        
        return success({
            "file_path": str(path.absolute()),
            "backup_id": backup_id,
            "size": len(content.encode(encoding))
        })
        
    except Exception as e:
        return failure("WRITE_ERROR", f"写入文件失败: {str(e)}")


def safe_file_delete(file_path: str) -> Dict[str, Any]:
    """
    安全的文件删除 - 自动备份和审计
    
    Args:
        file_path: 文件路径
        
    Returns:
        Codong风格的结果字典
    """
    path = Path(file_path)
    
    if not path.exists():
        return failure("FILE_NOT_FOUND", f"文件不存在: {file_path}")
    
    # 创建备份
    backup_id = None
    if _global_backup_manager:
        result = _global_backup_manager.create_backup(file_path)
        if not is_error(result):
            backup_info = unwrap(result)
            backup_id = backup_info["backup_id"]
    
    try:
        # 删除文件
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        
        # 记录审计日志
        if _global_audit_logger:
            _global_audit_logger.log(
                operation=AuditLogger.OP_FILE_DELETE,
                details={
                    "file_path": str(path.absolute()),
                    "backup_id": backup_id,
                    "was_directory": path.is_dir()
                },
                level=AuditLogger.LEVEL_WARNING
            )
        
        # 注册回滚
        if backup_id and _global_rollback_manager:
            _global_rollback_manager.register_operation(
                operation_type=AuditLogger.OP_FILE_DELETE,
                file_path=str(path.absolute()),
                backup_id=backup_id
            )
        
        return success({
            "file_path": str(path.absolute()),
            "backup_id": backup_id
        })
        
    except Exception as e:
        return failure("DELETE_ERROR", f"删除文件失败: {str(e)}")


# =============================================================================
# 模块测试
# =============================================================================

if __name__ == "__main__":
    # 初始化审计系统
    result = init_audit_system()
    
    if is_error(result):
        print(f"初始化失败: {result}")
        exit(1)
    
    print("审计系统初始化成功！")
    
    # 测试审计日志
    logger = get_audit_logger()
    if logger:
        # 记录测试日志
        result = logger.log(
            operation=AuditLogger.OP_USER_ACTION,
            details={"action": "test", "data": "example"}
        )
        print(f"记录日志: {result}")
        
        # 查询日志
        result = logger.query(limit=10)
        if not is_error(result):
            logs = unwrap(result)
            print(f"查询到 {len(logs)} 条日志")
        
        # 验证完整性
        result = logger.verify_integrity()
        print(f"完整性验证: {result}")
        
        # 获取统计
        result = logger.get_statistics()
        print(f"统计信息: {result}")
    
    # 测试备份管理
    backup_mgr = get_backup_manager()
    if backup_mgr:
        # 创建测试文件
        test_file = "/tmp/test_audit.txt"
        with open(test_file, 'w') as f:
            f.write("测试内容")
        
        # 创建备份
        result = backup_mgr.create_backup(test_file)
        print(f"创建备份: {result}")
        
        if not is_error(result):
            backup_info = unwrap(result)
            backup_id = backup_info["backup_id"]
            
            # 列出备份
            result = backup_mgr.list_backups(test_file)
            print(f"列出备份: {result}")
            
            # 恢复备份
            result = backup_mgr.restore_backup(backup_id)
            print(f"恢复备份: {result}")
    
    # 测试回滚管理
    rollback_mgr = get_rollback_manager()
    if rollback_mgr:
        # 获取操作历史
        result = rollback_mgr.get_operation_history()
        print(f"操作历史: {result}")
    
    # 测试安全写入
    result = safe_file_write("/tmp/test_safe_write.txt", "安全写入测试")
    print(f"安全写入: {result}")
    
    print("\n审计系统测试完成！")
