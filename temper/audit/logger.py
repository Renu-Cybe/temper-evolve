"""
审计日志器

提供结构化、防篡改的审计日志记录功能
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Callable, Optional, Any
from pathlib import Path
import json
import hashlib
import threading
import gzip


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = auto()
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class AuditCategory(Enum):
    """审计类别"""
    SYSTEM = "system"
    FILE_OPERATION = "file_operation"
    CONFIG_CHANGE = "config_change"
    USER_ACTION = "user_action"
    SELF_AWARENESS = "self_awareness"
    SELF_ADAPTIVE = "self_adaptive"
    SELF_ORGANIZING = "self_organizing"
    SELF_COMPILING = "self_compiling"
    SECURITY = "security"


@dataclass
class AuditRecord:
    """审计记录
    
    Attributes:
        id: 唯一标识符
        timestamp: 记录时间
        level: 审计级别
        category: 审计类别
        action: 操作名称
        source: 来源模块
        user: 用户标识（可选）
        parameters: 操作参数
        result: 操作结果（success/failure）
        error_message: 错误信息（如果有）
        context: 上下文信息
        correlation_id: 关联ID，用于追踪相关操作
        parent_id: 父操作ID（用于嵌套操作）
        previous_hash: 前一条记录的哈希（防篡改）
    """
    id: str
    timestamp: datetime
    level: AuditLevel
    category: AuditCategory
    action: str
    source: str
    user: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error_message: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    parent_id: Optional[str] = None
    previous_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.name,
            'category': self.category.value,
            'action': self.action,
            'source': self.source,
            'user': self.user,
            'parameters': self.parameters,
            'result': self.result,
            'error_message': self.error_message,
            'context': self.context,
            'correlation_id': self.correlation_id,
            'parent_id': self.parent_id,
            'previous_hash': self.previous_hash
        }
    
    def compute_hash(self) -> str:
        """计算记录哈希（用于防篡改链）"""
        # 排除 previous_hash 本身
        data = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.name,
            'category': self.category.value,
            'action': self.action,
            'source': self.source,
            'user': self.user,
            'parameters': self.parameters,
            'result': self.result,
            'error_message': self.error_message,
            'context': self.context,
            'correlation_id': self.correlation_id,
            'parent_id': self.parent_id
        }
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]


class AuditLogger:
    """审计日志器
    
    提供线程安全的审计日志记录，支持：
    - 结构化日志记录
    - 哈希链防篡改
    - 自动轮转和压缩
    - 缓冲区批量写入
    
    使用示例：
        logger = AuditLogger("data/audit")
        
        logger.info(
            category=AuditCategory.SYSTEM,
            action="system.start",
            source="main"
        )
        
        logger.close()
    """
    
    def __init__(self, storage_dir: str = "data/audit", 
                 max_file_size_mb: int = 100,
                 buffer_size: int = 100,
                 compression_enabled: bool = True):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Optional[Path] = None
        self._records: List[AuditRecord] = []
        self._last_hash: Optional[str] = None
        self._lock = threading.RLock()
        self._max_file_size_mb = max_file_size_mb
        self._max_buffer_size = buffer_size
        self._compression_enabled = compression_enabled
        self._sequence = 0
    
    def log(self, 
            level: AuditLevel,
            category: AuditCategory,
            action: str,
            source: str,
            parameters: Dict[str, Any] = None,
            result: str = None,
            error_message: str = None,
            context: Dict[str, Any] = None,
            user: str = None,
            correlation_id: str = None,
            parent_id: str = None) -> AuditRecord:
        """记录审计日志
        
        Args:
            level: 审计级别
            category: 审计类别
            action: 操作名称
            source: 来源模块
            parameters: 操作参数
            result: 操作结果
            error_message: 错误信息
            context: 上下文信息
            user: 用户标识
            correlation_id: 关联ID
            parent_id: 父操作ID
            
        Returns:
            创建的审计记录
        """
        with self._lock:
            self._sequence += 1
            
            record = AuditRecord(
                id=self._generate_id(),
                timestamp=datetime.now(),
                level=level,
                category=category,
                action=action,
                source=source,
                user=user,
                parameters=parameters or {},
                result=result,
                error_message=error_message,
                context=context or {},
                correlation_id=correlation_id,
                parent_id=parent_id,
                previous_hash=self._last_hash
            )
            
            self._records.append(record)
            self._last_hash = record.compute_hash()
            
            # 缓冲区满时写入文件
            if len(self._records) >= self._max_buffer_size:
                self._flush()
            
            return record
    
    def debug(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录 DEBUG 级别日志"""
        return self.log(AuditLevel.DEBUG, category, action, source, **kwargs)
    
    def info(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录 INFO 级别日志"""
        return self.log(AuditLevel.INFO, category, action, source, **kwargs)
    
    def warning(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录 WARNING 级别日志"""
        return self.log(AuditLevel.WARNING, category, action, source, **kwargs)
    
    def error(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录 ERROR 级别日志"""
        return self.log(AuditLevel.ERROR, category, action, source, **kwargs)
    
    def critical(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录 CRITICAL 级别日志"""
        return self.log(AuditLevel.CRITICAL, category, action, source, **kwargs)
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return f"{uuid.uuid4().hex[:8]}_{self._sequence}"
    
    def _flush(self) -> None:
        """将缓冲区写入文件"""
        if not self._records:
            return
        
        # 按日期分文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self._storage_dir / f"audit_{date_str}.log"
        
        # 检查文件大小，需要时轮转
        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb >= self._max_file_size_mb:
                self._rotate_file(log_file)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            for record in self._records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
        
        self._records = []
    
    def _rotate_file(self, log_file: Path) -> None:
        """轮转日志文件"""
        timestamp = datetime.now().strftime("%H%M%S")
        rotated = log_file.parent / f"{log_file.stem}_{timestamp}.log"
        log_file.rename(rotated)
        
        # 压缩旧文件
        if self._compression_enabled:
            self._compress_file(rotated)
    
    def _compress_file(self, file_path: Path) -> None:
        """压缩日志文件"""
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                    f_out.writelines(f_in)
            file_path.unlink()
        except Exception as e:
            print(f"Failed to compress {file_path}: {e}")
    
    def close(self) -> None:
        """关闭日志器，刷新缓冲区"""
        self._flush()
    
    def query(self, 
              start_time: Optional[datetime] = None,
              end_time: Optional[datetime] = None,
              category: Optional[AuditCategory] = None,
              level: Optional[AuditLevel] = None,
              source: Optional[str] = None,
              limit: int = 100) -> List[AuditRecord]:
        """查询审计日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            category: 审计类别
            level: 审计级别
            source: 来源模块
            limit: 返回记录数限制
            
        Returns:
            匹配的审计记录列表
        """
        records = []
        
        # 获取所有日志文件
        log_files = sorted(self._storage_dir.glob("audit_*.log*"))
        
        for log_file in log_files:
            # 解压缩如果需要
            if log_file.suffix == '.gz':
                try:
                    with gzip.open(log_file, 'rt', encoding='utf-8') as f:
                        for line in f:
                            record = self._parse_record(line)
                            if record and self._match_record(record, start_time, end_time, 
                                                             category, level, source):
                                records.append(record)
                except Exception:
                    continue
            else:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            record = self._parse_record(line)
                            if record and self._match_record(record, start_time, end_time,
                                                             category, level, source):
                                records.append(record)
                except Exception:
                    continue
        
        # 按时间排序并限制数量
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]
    
    def _parse_record(self, line: str) -> Optional[AuditRecord]:
        """解析审计记录"""
        try:
            data = json.loads(line)
            return AuditRecord(
                id=data['id'],
                timestamp=datetime.fromisoformat(data['timestamp']),
                level=AuditLevel[data['level']],
                category=AuditCategory(data['category']),
                action=data['action'],
                source=data['source'],
                user=data.get('user'),
                parameters=data.get('parameters', {}),
                result=data.get('result'),
                error_message=data.get('error_message'),
                context=data.get('context', {}),
                correlation_id=data.get('correlation_id'),
                parent_id=data.get('parent_id'),
                previous_hash=data.get('previous_hash')
            )
        except Exception:
            return None
    
    def _match_record(self, record: AuditRecord,
                      start_time: Optional[datetime],
                      end_time: Optional[datetime],
                      category: Optional[AuditCategory],
                      level: Optional[AuditLevel],
                      source: Optional[str]) -> bool:
        """检查记录是否匹配查询条件"""
        if start_time and record.timestamp < start_time:
            return False
        if end_time and record.timestamp > end_time:
            return False
        if category and record.category != category:
            return False
        if level and record.level != level:
            return False
        if source and record.source != source:
            return False
        return True
    
    def verify_chain(self, date_str: Optional[str] = None) -> bool:
        """验证审计链完整性
        
        Args:
            date_str: 日期字符串（如 "2024-01-15"），None 表示今天
            
        Returns:
            链是否完整
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        log_file = self._storage_dir / f"audit_{date_str}.log"
        if not log_file.exists():
            return True
        
        records = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                record = self._parse_record(line)
                if record:
                    records.append(record)
        
        # 验证哈希链
        for i, record in enumerate(records):
            if i > 0:
                expected_hash = records[i-1].compute_hash()
                if record.previous_hash != expected_hash:
                    return False
        
        return True
