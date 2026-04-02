# 四自系统架构设计文档

## 概述

四自系统（自感知、自适应、自组织、自编译）是一个遵循铁三角原则的智能系统架构，为 Temper AI Coding Agent 提供完整的自我管理能力。

## 铁三角原则

### 1. 信任原则
- **透明可审计**：所有操作记录可追溯
- **不擅自修改用户文件**：任何文件修改需用户确认
- **操作可回溯**：支持撤销和回滚

### 2. 复利原则
- **能力持久化**：学习到的能力保存到磁盘
- **下次启动继承**：状态自动恢复
- **状态可恢复**：支持快照和回滚

### 3. 杠杆原则
- **配置驱动**：拒绝硬编码
- **通过配置控制行为**：所有行为可配置
- **插件化扩展**：支持动态加载

---

## 目录结构

```
temper/
├── __init__.py                    # 包初始化
├── __main__.py                    # 入口点
│
├── core/                          # 核心基础设施
│   ├── __init__.py
│   ├── errors.py                  # Codong 错误处理（已有）
│   ├── result.py                  # Result 类型定义
│   ├── events.py                  # 事件系统
│   └── types.py                   # 共享类型定义
│
├── config/                        # 配置系统
│   ├── __init__.py
│   ├── manager.py                 # 配置管理器
│   ├── schema.py                  # 配置模式定义
│   ├── loader.py                  # 配置加载器
│   └── defaults.yaml              # 默认配置
│
├── audit/                         # 审计系统
│   ├── __init__.py
│   ├── logger.py                  # 审计日志
│   ├── tracer.py                  # 操作追踪
│   ├── storage.py                 # 审计存储
│   └── replay.py                  # 操作回放
│
├── persistence/                   # 持久化系统
│   ├── __init__.py
│   ├── manager.py                 # 持久化管理器
│   ├── serializers.py             # 序列化器
│   ├── storage.py                 # 存储后端
│   └── snapshot.py                # 快照管理
│
├── self_awareness/                # 自感知模块
│   ├── __init__.py
│   ├── monitor.py                 # 健康监控
│   ├── metrics.py                 # 指标收集
│   ├── diagnostics.py             # 诊断系统
│   ├── resources.py               # 资源监控
│   └── reporters/                 # 报告器
│       ├── __init__.py
│       ├── console.py
│       └── file.py
│
├── self_adaptive/                 # 自适应模块
│   ├── __init__.py
│   ├── tuner.py                   # 参数调优
│   ├── optimizer.py               # 性能优化
│   ├── balancer.py                # 负载均衡
│   ├── strategies.py              # 自适应策略
│   └── rules.py                   # 规则引擎
│
├── self_organizing/               # 自组织模块
│   ├── __init__.py
│   ├── workflow.py                # 工作流引擎
│   ├── orchestrator.py            # 任务编排
│   ├── scheduler.py               # 任务调度
│   ├── dependency.py              # 依赖管理
│   └── graph.py                   # 依赖图
│
├── self_compiling/                # 自编译模块
│   ├── __init__.py
│   ├── repair.py                  # 自我修复
│   ├── generator.py               # 代码生成
│   ├── hotload.py                 # 热加载
│   ├── validator.py               # 代码验证
│   └── templates/                 # 代码模板
│
├── tools/                         # 工具系统（已有）
│   ├── __init__.py
│   └── tools.py
│
└── data/                          # 数据目录
    ├── config/                    # 配置文件
    ├── audit/                     # 审计日志
    ├── state/                     # 状态数据
    └── snapshots/                 # 快照数据
```

---

## 模块详细设计

### 1. 核心基础设施 (core/)

#### 1.1 Result 类型 (result.py)

```python
"""
Result 类型 - Codong 风格的错误处理

遵循铁三角原则：
- 信任：显式错误处理，不隐藏异常
- 复利：统一的错误处理模式
- 杠杆：可扩展的错误类型
"""

from typing import TypeVar, Generic, Union, Callable, Optional
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')
E = TypeVar('E')

class ErrorCode(Enum):
    """错误代码枚举"""
    # 系统级错误
    SYSTEM_ERROR = "system_error"
    CONFIG_ERROR = "config_error"
    
    # 运行时错误
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # 业务错误
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    
    # 自感知错误
    HEALTH_CHECK_FAILED = "health_check_failed"
    METRIC_COLLECTION_FAILED = "metric_collection_failed"
    
    # 自适应错误
    TUNING_FAILED = "tuning_failed"
    OPTIMIZATION_FAILED = "optimization_failed"
    
    # 自组织错误
    WORKFLOW_ERROR = "workflow_error"
    DEPENDENCY_ERROR = "dependency_error"
    
    # 自编译错误
    REPAIR_FAILED = "repair_failed"
    GENERATION_FAILED = "generation_failed"
    HOTLOAD_FAILED = "hotload_failed"

@dataclass(frozen=True)
class Error:
    """错误类型"""
    code: ErrorCode
    message: str
    context: dict = None
    cause: Optional['Error'] = None
    
    def __post_init__(self):
        if self.context is None:
            object.__setattr__(self, 'context', {})
    
    def with_context(self, **kwargs) -> 'Error':
        """添加上下文信息"""
        new_context = {**self.context, **kwargs}
        return Error(self.code, self.message, new_context, self.cause)
    
    def __str__(self) -> str:
        base = f"[{self.code.value}] {self.message}"
        if self.context:
            base += f" | context: {self.context}"
        if self.cause:
            base += f" | caused by: {self.cause}"
        return base

@dataclass(frozen=True)
class Ok(Generic[T]):
    """成功结果"""
    value: T
    
    def is_ok(self) -> bool:
        return True
    
    def is_error(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        return self.value
    
    def map(self, f: Callable[[T], 'Result']) -> 'Result':
        return f(self.value)

@dataclass(frozen=True)
class Err(Generic[E]):
    """错误结果"""
    error: Error
    
    def is_ok(self) -> bool:
        return False
    
    def is_error(self) -> bool:
        return True
    
    def unwrap(self) -> None:
        raise RuntimeError(f"Called unwrap on Err: {self.error}")
    
    def unwrap_or(self, default: T) -> T:
        return default
    
    def map(self, f: Callable) -> 'Result':
        return self

Result = Union[Ok[T], Err]

# 便捷函数
def ok(value: T) -> Result[T, None]:
    """创建成功结果"""
    return Ok(value)

def err(code: ErrorCode, message: str, **context) -> Result[None, Error]:
    """创建错误结果"""
    return Err(Error(code, message, context))

def is_ok(result: Result) -> bool:
    """检查结果是否成功"""
    return isinstance(result, Ok)

def is_error(result: Result) -> bool:
    """检查结果是否错误"""
    return isinstance(result, Err)

def unwrap(result: Result[T, Error]) -> T:
    """解包结果"""
    if isinstance(result, Ok):
        return result.value
    raise RuntimeError(f"Cannot unwrap Err: {result.error}")

def unwrap_or(result: Result[T, Error], default: T) -> T:
    """解包结果或返回默认值"""
    if isinstance(result, Ok):
        return result.value
    return default
```

#### 1.2 事件系统 (events.py)

```python
"""
事件系统 - 模块间通信的基础设施

遵循铁三角原则：
- 信任：所有事件可审计
- 复利：事件历史可查询
- 杠杆：事件处理器可配置
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading
from queue import Queue

class EventType(Enum):
    """事件类型"""
    # 系统事件
    SYSTEM_START = auto()
    SYSTEM_STOP = auto()
    SYSTEM_ERROR = auto()
    
    # 自感知事件
    HEALTH_CHECK = auto()
    METRIC_COLLECTED = auto()
    ALERT_TRIGGERED = auto()
    
    # 自适应事件
    PARAMETER_TUNED = auto()
    OPTIMIZATION_APPLIED = auto()
    LOAD_BALANCED = auto()
    
    # 自组织事件
    WORKFLOW_CREATED = auto()
    TASK_SCHEDULED = auto()
    DEPENDENCY_RESOLVED = auto()
    
    # 自编译事件
    CODE_GENERATED = auto()
    CODE_REPAIRED = auto()
    HOTLOAD_COMPLETED = auto()
    
    # 配置事件
    CONFIG_CHANGED = auto()
    CONFIG_RELOADED = auto()

@dataclass
class Event:
    """事件对象"""
    type: EventType
    source: str                    # 事件来源模块
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None  # 关联ID，用于追踪
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.name,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id
        }

class EventBus:
    """事件总线 - 中心化事件管理"""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()
        self._event_queue: Queue = Queue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
    
    def subscribe(self, event_type: EventType, 
                  handler: Callable[[Event], None]) -> None:
        """订阅事件"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType,
                    handler: Callable[[Event], None]) -> None:
        """取消订阅"""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type].remove(handler)
    
    def publish(self, event: Event) -> None:
        """发布事件"""
        self._event_queue.put(event)
    
    def publish_sync(self, event: Event) -> None:
        """同步发布事件（立即处理）"""
        handlers = []
        with self._lock:
            handlers = self._handlers.get(event.type, []).copy()
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # 记录错误但不中断其他处理器
                print(f"Event handler error: {e}")
    
    def start(self) -> None:
        """启动事件处理循环"""
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop)
        self._worker_thread.daemon = True
        self._worker_thread.start()
    
    def stop(self) -> None:
        """停止事件处理循环"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
    
    def _process_loop(self) -> None:
        """事件处理循环"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1)
                self.publish_sync(event)
            except Exception:
                continue

# 全局事件总线实例
event_bus = EventBus()
```

---

### 2. 配置系统 (config/)

```python
"""
配置系统 - 杠杆原则的核心实现

设计原则：
1. 配置驱动：所有行为通过配置控制
2. 分层配置：默认 < 文件 < 环境变量 < 运行时
3. 类型安全：配置项有明确的类型和验证
4. 热重载：支持配置动态更新
"""

# config/schema.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "temper"
    version: str = "2.0.0"
    log_level: LogLevel = LogLevel.INFO
    max_workers: int = 4
    
@dataclass
class SelfAwarenessConfig:
    """自感知模块配置"""
    enabled: bool = True
    health_check_interval: int = 30           # 秒
    metrics_collection_interval: int = 10     # 秒
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'cpu_percent': 80.0,
        'memory_percent': 85.0,
        'disk_percent': 90.0,
        'response_time_ms': 5000
    })
    retention_days: int = 7

@dataclass
class SelfAdaptiveConfig:
    """自适应模块配置"""
    enabled: bool = True
    tuning_interval: int = 300                # 秒
    optimization_enabled: bool = True
    load_balance_enabled: bool = True
    auto_scale: bool = False
    
    # 参数调优配置
    tuning_params: Dict[str, Any] = field(default_factory=lambda: {
        'temperature_range': [0.1, 1.0],
        'max_tokens_range': [1024, 8192],
        'learning_rate': 0.01
    })

@dataclass
class SelfOrganizingConfig:
    """自组织模块配置"""
    enabled: bool = True
    max_concurrent_tasks: int = 10
    task_timeout: int = 300                   # 秒
    retry_attempts: int = 3
    retry_delay: int = 5                      # 秒
    
    # 工作流配置
    workflow_defaults: Dict[str, Any] = field(default_factory=lambda: {
        'parallel_limit': 5,
        'dependency_resolution': 'automatic'
    })

@dataclass
class SelfCompilingConfig:
    """自编译模块配置"""
    enabled: bool = True
    auto_repair: bool = False                 # 需要用户确认
    auto_generate: bool = False               # 需要用户确认
    hotload_enabled: bool = True
    
    # 代码生成配置
    generation: Dict[str, Any] = field(default_factory=lambda: {
        'template_dir': 'templates',
        'output_dir': 'generated',
        'validation_enabled': True
    })
    
    # 热加载配置
    hotload: Dict[str, Any] = field(default_factory=lambda: {
        'watch_patterns': ['*.py'],
        'exclude_patterns': ['__pycache__/*'],
        'cooldown_seconds': 2
    })

@dataclass
class AuditConfig:
    """审计配置"""
    enabled: bool = True
    log_level: str = "info"
    storage_type: str = "file"                # file, database
    retention_days: int = 30
    max_file_size_mb: int = 100
    
@dataclass
class PersistenceConfig:
    """持久化配置"""
    enabled: bool = True
    storage_dir: str = "data"
    auto_save_interval: int = 60              # 秒
    snapshot_interval: int = 3600             # 秒
    max_snapshots: int = 10

@dataclass
class Config:
    """完整配置"""
    system: SystemConfig = field(default_factory=SystemConfig)
    self_awareness: SelfAwarenessConfig = field(default_factory=SelfAwarenessConfig)
    self_adaptive: SelfAdaptiveConfig = field(default_factory=SelfAdaptiveConfig)
    self_organizing: SelfOrganizingConfig = field(default_factory=SelfOrganizingConfig)
    self_compiling: SelfCompilingConfig = field(default_factory=SelfCompilingConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    
    # 自定义配置（插件等）
    custom: Dict[str, Any] = field(default_factory=dict)


# config/manager.py
import os
import yaml
import json
from typing import Optional, Any
from pathlib import Path
from .schema import Config
from ..core.result import Result, ok, err, ErrorCode

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "data/config"):
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.yaml"
        self._config: Config = Config()
        self._listeners: list = []
    
    def load(self) -> Result[Config, Any]:
        """加载配置"""
        try:
            # 1. 加载默认配置
            config = Config()
            
            # 2. 从文件加载
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        config = self._merge_config(config, data)
            
            # 3. 从环境变量加载
            config = self._load_from_env(config)
            
            self._config = config
            return ok(config)
            
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to load config: {e}")
    
    def save(self) -> Result[bool, Any]:
        """保存配置"""
        try:
            data = self._config_to_dict(self._config)
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return ok(True)
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to save config: {e}")
    
    def get(self) -> Config:
        """获取当前配置"""
        return self._config
    
    def update(self, path: str, value: Any) -> Result[bool, Any]:
        """更新配置项（支持点号路径）"""
        try:
            parts = path.split('.')
            target = self._config
            
            for part in parts[:-1]:
                target = getattr(target, part)
            
            setattr(target, parts[-1], value)
            
            # 通知监听器
            self._notify_change(path, value)
            
            return ok(True)
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to update config: {e}")
    
    def register_listener(self, callback: callable) -> None:
        """注册配置变更监听器"""
        self._listeners.append(callback)
    
    def _notify_change(self, path: str, value: Any) -> None:
        """通知配置变更"""
        for listener in self._listeners:
            try:
                listener(path, value)
            except Exception:
                pass
    
    def _merge_config(self, config: Config, data: dict) -> Config:
        """合并配置数据"""
        # 递归合并字典
        def merge_dict(target: dict, source: dict) -> dict:
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dict(target[key], value)
                else:
                    target[key] = value
            return target
        
        config_dict = self._config_to_dict(config)
        merged = merge_dict(config_dict, data)
        return self._dict_to_config(merged)
    
    def _load_from_env(self, config: Config) -> Config:
        """从环境变量加载配置"""
        # 支持 TEMPER_ 前缀的环境变量
        prefix = "TEMPER_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                path = key[len(prefix):].lower().replace('_', '.')
                # 尝试转换类型
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
                self.update(path, value)
        
        return config
    
    def _config_to_dict(self, config: Config) -> dict:
        """配置对象转字典"""
        from dataclasses import asdict
        return asdict(config)
    
    def _dict_to_config(self, data: dict) -> Config:
        """字典转配置对象"""
        # 简化实现，实际可能需要更复杂的反序列化
        return Config(**data)
```

---

### 3. 审计系统 (audit/)

```python
"""
审计系统 - 信任原则的核心实现

设计原则：
1. 透明可审计：所有操作记录可追溯
2. 不可篡改：审计日志防篡改
3. 可回放：支持操作回放
4. 结构化：统一的审计记录格式
"""

# audit/logger.py
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import hashlib
import threading

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

@dataclass
class AuditRecord:
    """审计记录"""
    id: str                                    # 唯一ID
    timestamp: datetime                        # 时间戳
    level: AuditLevel                          # 级别
    category: AuditCategory                    # 类别
    action: str                                # 操作名称
    source: str                                # 来源模块
    user: Optional[str]                        # 用户标识
    
    # 操作详情
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None               # 结果：success, failure
    error_message: Optional[str] = None
    
    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None       # 关联ID
    parent_id: Optional[str] = None            # 父操作ID
    
    # 完整性
    previous_hash: Optional[str] = None        # 前一条记录哈希
    
    def to_dict(self) -> dict:
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
        """计算记录哈希"""
        data = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

class AuditLogger:
    """审计日志器"""
    
    def __init__(self, storage_dir: str = "data/audit"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Optional[Path] = None
        self._records: List[AuditRecord] = []
        self._last_hash: Optional[str] = None
        self._lock = threading.RLock()
        self._max_buffer_size = 100
    
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
        """记录审计日志"""
        with self._lock:
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
    
    def info(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录信息级别日志"""
        return self.log(AuditLevel.INFO, category, action, source, **kwargs)
    
    def warning(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录警告级别日志"""
        return self.log(AuditLevel.WARNING, category, action, source, **kwargs)
    
    def error(self, category: AuditCategory, action: str, source: str, **kwargs) -> AuditRecord:
        """记录错误级别日志"""
        return self.log(AuditLevel.ERROR, category, action, source, **kwargs)
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _flush(self) -> None:
        """将缓冲区写入文件"""
        if not self._records:
            return
        
        # 按日期分文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self._storage_dir / f"audit_{date_str}.log"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            for record in self._records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
        
        self._records = []
    
    def close(self) -> None:
        """关闭日志器，刷新缓冲区"""
        self._flush()


# audit/tracer.py
from contextlib import contextmanager
from typing import Optional, Dict, Any
from .logger import AuditLogger, AuditCategory, AuditLevel
import uuid

class OperationTracer:
    """操作追踪器 - 追踪操作的完整生命周期"""
    
    def __init__(self, audit_logger: AuditLogger):
        self._audit = audit_logger
        self._context_stack: list = []
    
    @contextmanager
    def trace(self, 
              category: AuditCategory,
              action: str,
              source: str,
              parameters: Dict[str, Any] = None,
              user: str = None):
        """追踪操作上下文"""
        correlation_id = str(uuid.uuid4())[:8]
        parent_id = self._context_stack[-1] if self._context_stack else None
        
        # 记录开始
        record = self._audit.log(
            level=AuditLevel.INFO,
            category=category,
            action=f"{action}.start",
            source=source,
            parameters=parameters,
            correlation_id=correlation_id,
            parent_id=parent_id,
            user=user
        )
        
        self._context_stack.append(record.id)
        
        try:
            yield record
            # 记录成功
            self._audit.log(
                level=AuditLevel.INFO,
                category=category,
                action=f"{action}.complete",
                source=source,
                result="success",
                correlation_id=correlation_id,
                parent_id=parent_id,
                user=user
            )
        except Exception as e:
            # 记录失败
            self._audit.log(
                level=AuditLevel.ERROR,
                category=category,
                action=f"{action}.failed",
                source=source,
                result="failure",
                error_message=str(e),
                correlation_id=correlation_id,
                parent_id=parent_id,
                user=user
            )
            raise
        finally:
            self._context_stack.pop()
    
    def get_current_context(self) -> Optional[str]:
        """获取当前上下文ID"""
        return self._context_stack[-1] if self._context_stack else None
```

---

### 4. 持久化系统 (persistence/)

```python
"""
持久化系统 - 复利原则的核心实现

设计原则：
1. 能力持久化：学习到的能力保存到磁盘
2. 状态可恢复：支持快照和回滚
3. 多后端支持：文件、数据库等
4. 序列化灵活：JSON、MessagePack等
"""

# persistence/serializers.py
from typing import Any, Protocol
import json
import pickle

class Serializer(Protocol):
    """序列化器协议"""
    
    def serialize(self, obj: Any) -> bytes:
        ...
    
    def deserialize(self, data: bytes) -> Any:
        ...
    
    @property
    def content_type(self) -> str:
        ...

class JSONSerializer:
    """JSON序列化器"""
    
    def serialize(self, obj: Any) -> bytes:
        return json.dumps(obj, ensure_ascii=False, default=str).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))
    
    @property
    def content_type(self) -> str:
        return "application/json"

class PickleSerializer:
    """Pickle序列化器（仅用于内部状态）"""
    
    def serialize(self, obj: Any) -> bytes:
        return pickle.dumps(obj)
    
    def deserialize(self, data: bytes) -> Any:
        return pickle.loads(data)
    
    @property
    def content_type(self) -> str:
        return "application/python-pickle"


# persistence/storage.py
from pathlib import Path
from typing import Optional, List, Protocol
from datetime import datetime
from .serializers import Serializer, JSONSerializer

class StorageBackend(Protocol):
    """存储后端协议"""
    
    def save(self, key: str, data: bytes) -> bool:
        ...
    
    def load(self, key: str) -> Optional[bytes]:
        ...
    
    def delete(self, key: str) -> bool:
        ...
    
    def list_keys(self, prefix: str = "") -> List[str]:
        ...
    
    def exists(self, key: str) -> bool:
        ...

class FileStorageBackend:
    """文件存储后端"""
    
    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, key: str) -> Path:
        """获取文件路径"""
        # 将key中的/转换为目录结构
        return self._base_dir / key
    
    def save(self, key: str, data: bytes) -> bool:
        try:
            path = self._get_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
            return True
        except Exception:
            return False
    
    def load(self, key: str) -> Optional[bytes]:
        try:
            path = self._get_path(key)
            if not path.exists():
                return None
            with open(path, 'rb') as f:
                return f.read()
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        try:
            path = self._get_path(key)
            if path.exists():
                path.unlink()
            return True
        except Exception:
            return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        try:
            pattern = f"{prefix}*" if prefix else "*"
            paths = list(self._base_dir.rglob(pattern))
            return [str(p.relative_to(self._base_dir)) for p in paths if p.is_file()]
        except Exception:
            return []
    
    def exists(self, key: str) -> bool:
        return self._get_path(key).exists()


# persistence/snapshot.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import shutil

@dataclass
class Snapshot:
    """快照对象"""
    id: str
    timestamp: datetime
    description: str
    state_hash: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'state_hash': self.state_hash,
            'metadata': self.metadata
        }

class SnapshotManager:
    """快照管理器"""
    
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
            with open(self._index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for snap_data in data.get('snapshots', []):
                    snapshot = Snapshot(
                        id=snap_data['id'],
                        timestamp=datetime.fromisoformat(snap_data['timestamp']),
                        description=snap_data['description'],
                        state_hash=snap_data['state_hash'],
                        metadata=snap_data.get('metadata', {})
                    )
                    self._snapshots[snapshot.id] = snapshot
    
    def _save_index(self) -> None:
        """保存快照索引"""
        data = {
            'snapshots': [s.to_dict() for s in self._snapshots.values()]
        }
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create(self, 
               state_data: bytes,
               description: str = "",
               metadata: Dict[str, Any] = None) -> Snapshot:
        """创建快照"""
        import hashlib
        import uuid
        
        snapshot_id = str(uuid.uuid4())[:8]
        state_hash = hashlib.sha256(state_data).hexdigest()[:16]
        
        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=datetime.now(),
            description=description,
            state_hash=state_hash,
            metadata=metadata or {}
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
        """恢复快照"""
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if not state_file.exists():
            return None
        
        with open(state_file, 'rb') as f:
            return f.read()
    
    def list_snapshots(self) -> List[Snapshot]:
        """列出所有快照"""
        return sorted(self._snapshots.values(), 
                     key=lambda s: s.timestamp, reverse=True)
    
    def delete(self, snapshot_id: str) -> bool:
        """删除快照"""
        if snapshot_id not in self._snapshots:
            return False
        
        state_file = self._state_dir / f"{snapshot_id}.dat"
        if state_file.exists():
            state_file.unlink()
        
        del self._snapshots[snapshot_id]
        self._save_index()
        
        return True
    
    def cleanup_old_snapshots(self, max_count: int = 10) -> int:
        """清理旧快照"""
        snapshots = self.list_snapshots()
        if len(snapshots) <= max_count:
            return 0
        
        deleted = 0
        for snapshot in snapshots[max_count:]:
            if self.delete(snapshot.id):
                deleted += 1
        
        return deleted
```

---

### 5. 自感知模块 (self_awareness/)

```python
"""
自感知模块 - 系统的"神经系统"

功能：
1. 健康自检：定期检查系统健康状态
2. 状态监控：收集和报告系统状态
3. 资源监控：监控CPU、内存、磁盘等资源
4. 告警管理：基于阈值触发告警
"""

# self_awareness/metrics.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
import threading
import time
import psutil

class MetricType(Enum):
    """指标类型"""
    GAUGE = "gauge"           # 瞬时值
    COUNTER = "counter"       # 累计值
    HISTOGRAM = "histogram"   # 分布值

@dataclass
class MetricValue:
    """指标值"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._collectors: Dict[str, Callable[[], MetricValue]] = {}
        self._metrics_history: List[MetricValue] = []
        self._lock = threading.RLock()
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._interval = 10  # 秒
    
    def register(self, name: str, collector: Callable[[], MetricValue]) -> None:
        """注册指标收集器"""
        with self._lock:
            self._collectors[name] = collector
    
    def collect(self) -> List[MetricValue]:
        """执行一次指标收集"""
        metrics = []
        with self._lock:
            for name, collector in self._collectors.items():
                try:
                    metric = collector()
                    metrics.append(metric)
                except Exception as e:
                    print(f"Failed to collect metric {name}: {e}")
        
        with self._lock:
            self._metrics_history.extend(metrics)
            # 限制历史大小
            if len(self._metrics_history) > 10000:
                self._metrics_history = self._metrics_history[-5000:]
        
        return metrics
    
    def get_history(self, name: Optional[str] = None, 
                    limit: int = 100) -> List[MetricValue]:
        """获取指标历史"""
        with self._lock:
            history = self._metrics_history
            if name:
                history = [m for m in history if m.name == name]
            return history[-limit:]
    
    def start_collection(self, interval: int = 10) -> None:
        """启动自动收集"""
        self._interval = interval
        self._running = True
        self._collection_thread = threading.Thread(target=self._collection_loop)
        self._collection_thread.daemon = True
        self._collection_thread.start()
    
    def stop_collection(self) -> None:
        """停止自动收集"""
        self._running = False
    
    def _collection_loop(self) -> None:
        """收集循环"""
        while self._running:
            self.collect()
            time.sleep(self._interval)


# self_awareness/resources.py
class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics = metrics_collector
        self._register_default_collectors()
    
    def _register_default_collectors(self) -> None:
        """注册默认资源收集器"""
        
        # CPU使用率
        self._metrics.register("cpu_percent", self._collect_cpu)
        
        # 内存使用
        self._metrics.register("memory_percent", self._collect_memory)
        
        # 磁盘使用
        self._metrics.register("disk_percent", self._collect_disk)
        
        # 网络IO
        self._metrics.register("net_io", self._collect_network)
    
    def _collect_cpu(self) -> MetricValue:
        return MetricValue(
            name="cpu_percent",
            value=psutil.cpu_percent(interval=1),
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_memory(self) -> MetricValue:
        mem = psutil.virtual_memory()
        return MetricValue(
            name="memory_percent",
            value=mem.percent,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_disk(self) -> MetricValue:
        disk = psutil.disk_usage('/')
        return MetricValue(
            name="disk_percent",
            value=(disk.used / disk.total) * 100,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_network(self) -> MetricValue:
        net = psutil.net_io_counters()
        return MetricValue(
            name="net_io_bytes",
            value=net.bytes_sent + net.bytes_recv,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            unit="bytes"
        )


# self_awareness/diagnostics.py
from typing import Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """健康检查项"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict = None

class Diagnostics:
    """诊断系统"""
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._last_results: Dict[str, HealthCheck] = {}
    
    def register_check(self, name: str, 
                       check_func: Callable[[], HealthCheck]) -> None:
        """注册健康检查"""
        self._checks[name] = check_func
    
    def run_check(self, name: str) -> HealthCheck:
        """运行单个健康检查"""
        if name not in self._checks:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not registered",
                timestamp=datetime.now()
            )
        
        try:
            result = self._checks[name]()
            self._last_results[name] = result
            return result
        except Exception as e:
            result = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                timestamp=datetime.now()
            )
            self._last_results[name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """运行所有健康检查"""
        results = {}
        for name in self._checks:
            results[name] = self.run_check(name)
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self._last_results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in self._last_results.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
```

---

### 6. 自适应模块 (self_adaptive/)

```python
"""
自适应模块 - 系统的"调节系统"

功能：
1. 动态调参：根据负载自动调整参数
2. 性能优化：识别瓶颈并优化
3. 负载均衡：在多个资源间分配负载
4. 策略管理：定义和执行自适应策略
"""

# self_adaptive/tuner.py
from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
import threading
import time

@dataclass
class Parameter:
    """可调参数"""
    name: str
    current_value: Any
    min_value: Any
    max_value: Any
    step: Any
    description: str = ""

@dataclass
class TuningResult:
    """调优结果"""
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: datetime
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]

class ParameterTuner:
    """参数调优器"""
    
    def __init__(self, metrics_collector):
        self._metrics = metrics_collector
        self._parameters: Dict[str, Parameter] = {}
        self._adjusters: Dict[str, Callable[[Parameter, Dict], Any]] = {}
        self._history: List[TuningResult] = []
        self._lock = threading.RLock()
        self._running = False
    
    def register_parameter(self, param: Parameter) -> None:
        """注册可调参数"""
        with self._lock:
            self._parameters[param.name] = param
    
    def register_adjuster(self, param_name: str, 
                          adjuster: Callable[[Parameter, Dict], Any]) -> None:
        """注册参数调整器"""
        with self._lock:
            self._adjusters[param_name] = adjuster
    
    def tune(self, param_name: str, 
             reason: str = "") -> Optional[TuningResult]:
        """调优指定参数"""
        with self._lock:
            if param_name not in self._parameters:
                return None
            
            param = self._parameters[param_name]
            
            # 获取当前指标
            metrics_before = self._get_current_metrics()
            
            # 执行调整
            if param_name in self._adjusters:
                new_value = self._adjusters[param_name](param, metrics_before)
            else:
                # 默认调整逻辑
                new_value = self._default_adjust(param, metrics_before)
            
            if new_value == param.current_value:
                return None
            
            old_value = param.current_value
            param.current_value = new_value
            
            # 等待并获取新指标
            time.sleep(1)
            metrics_after = self._get_current_metrics()
            
            result = TuningResult(
                parameter=param_name,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                timestamp=datetime.now(),
                metrics_before=metrics_before,
                metrics_after=metrics_after
            )
            
            self._history.append(result)
            return result
    
    def _get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        # 简化实现
        return {}
    
    def _default_adjust(self, param: Parameter, 
                        metrics: Dict[str, float]) -> Any:
        """默认调整逻辑"""
        # 简单的递增/递减逻辑
        current = param.current_value
        if isinstance(current, (int, float)):
            if metrics.get('cpu_percent', 0) > 80:
                return max(param.min_value, current - param.step)
            elif metrics.get('cpu_percent', 0) < 30:
                return min(param.max_value, current + param.step)
        return current
    
    def get_history(self, limit: int = 100) -> List[TuningResult]:
        """获取调优历史"""
        return self._history[-limit:]


# self_adaptive/strategies.py
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum

class StrategyType(Enum):
    """策略类型"""
    THRESHOLD = "threshold"       # 阈值策略
    PREDICTIVE = "predictive"     # 预测策略
    REINFORCEMENT = "rl"          # 强化学习策略
    RULE_BASED = "rule_based"     # 规则策略

@dataclass
class AdaptiveStrategy:
    """自适应策略"""
    name: str
    strategy_type: StrategyType
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True

class StrategyEngine:
    """策略引擎"""
    
    def __init__(self, metrics_collector, parameter_tuner):
        self._metrics = metrics_collector
        self._tuner = parameter_tuner
        self._strategies: List[AdaptiveStrategy] = []
        self._action_handlers: Dict[str, Callable] = {}
    
    def register_strategy(self, strategy: AdaptiveStrategy) -> None:
        """注册策略"""
        self._strategies.append(strategy)
        # 按优先级排序
        self._strategies.sort(key=lambda s: s.priority, reverse=True)
    
    def register_action_handler(self, action_type: str, 
                                handler: Callable) -> None:
        """注册动作处理器"""
        self._action_handlers[action_type] = handler
    
    def evaluate(self) -> List[Dict]:
        """评估所有策略"""
        triggered = []
        
        for strategy in self._strategies:
            if not strategy.enabled:
                continue
            
            if self._check_conditions(strategy.conditions):
                actions = self._execute_actions(strategy.actions)
                triggered.append({
                    'strategy': strategy.name,
                    'actions': actions
                })
        
        return triggered
    
    def _check_conditions(self, conditions: List[Dict]) -> bool:
        """检查条件是否满足"""
        # 简化实现
        return True
    
    def _execute_actions(self, actions: List[Dict]) -> List[Any]:
        """执行动作"""
        results = []
        for action in actions:
            action_type = action.get('type')
            if action_type in self._action_handlers:
                result = self._action_handlers[action_type](action)
                results.append(result)
        return results
```

---

### 7. 自组织模块 (self_organizing/)

```python
"""
自组织模块 - 系统的"协调系统"

功能：
1. 工作流合成：动态组合任务流程
2. 任务编排：管理任务执行顺序
3. 依赖管理：解析和处理任务依赖
4. 调度优化：优化任务调度策略
"""

# self_organizing/graph.py
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum

class NodeState(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskNode:
    """任务节点"""
    id: str
    name: str
    dependencies: Set[str] = field(default_factory=set)
    state: NodeState = NodeState.PENDING
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class DependencyGraph:
    """依赖图"""
    
    def __init__(self):
        self._nodes: Dict[str, TaskNode] = {}
        self._edges: Dict[str, Set[str]] = {}  # node -> dependents
    
    def add_node(self, node: TaskNode) -> None:
        """添加节点"""
        self._nodes[node.id] = node
        if node.id not in self._edges:
            self._edges[node.id] = set()
        
        # 建立依赖关系
        for dep_id in node.dependencies:
            if dep_id not in self._edges:
                self._edges[dep_id] = set()
            self._edges[dep_id].add(node.id)
    
    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """获取节点"""
        return self._nodes.get(node_id)
    
    def get_ready_nodes(self) -> List[TaskNode]:
        """获取就绪节点（依赖已满足）"""
        ready = []
        for node in self._nodes.values():
            if node.state != NodeState.PENDING:
                continue
            
            # 检查所有依赖是否完成
            deps_satisfied = all(
                self._nodes.get(dep_id, TaskNode(dep_id, "")).state == NodeState.COMPLETED
                for dep_id in node.dependencies
            )
            
            if deps_satisfied:
                ready.append(node)
        
        return ready
    
    def get_dependents(self, node_id: str) -> Set[str]:
        """获取依赖该节点的所有节点"""
        return self._edges.get(node_id, set())
    
    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        visited = set()
        result = []
        
        def visit(node_id: str, visiting: Set[str]):
            if node_id in visiting:
                raise ValueError(f"Circular dependency detected at {node_id}")
            if node_id in visited:
                return
            
            visiting.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    visit(dep_id, visiting)
            visiting.remove(node_id)
            
            visited.add(node_id)
            result.append(node_id)
        
        for node_id in self._nodes:
            if node_id not in visited:
                visit(node_id, set())
        
        return result
    
    def detect_cycles(self) -> Optional[List[str]]:
        """检测循环依赖"""
        try:
            self.topological_sort()
            return None
        except ValueError as e:
            return str(e)


# self_organizing/scheduler.py
from typing import Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from datetime import datetime
from .graph import DependencyGraph, TaskNode, NodeState

@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    success: bool
    result: Any
    error: Optional[str]
    start_time: datetime
    end_time: datetime

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 4):
        self._graph = DependencyGraph()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_handlers: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, Future] = {}
        self._results: Dict[str, TaskResult] = {}
    
    def register_task_handler(self, task_type: str, 
                              handler: Callable) -> None:
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
    
    def add_task(self, node: TaskNode) -> None:
        """添加任务"""
        self._graph.add_node(node)
    
    def execute(self) -> Dict[str, TaskResult]:
        """执行所有任务"""
        # 检查循环依赖
        cycle = self._graph.detect_cycles()
        if cycle:
            raise ValueError(f"Cannot execute: {cycle}")
        
        while True:
            # 获取就绪任务
            ready_nodes = self._graph.get_ready_nodes()
            
            if not ready_nodes and not self._running_tasks:
                break  # 所有任务完成
            
            # 启动就绪任务
            for node in ready_nodes:
                self._start_task(node)
            
            # 等待至少一个任务完成
            self._wait_for_any()
        
        return self._results
    
    def _start_task(self, node: TaskNode) -> None:
        """启动任务"""
        node.state = NodeState.RUNNING
        start_time = datetime.now()
        
        task_type = node.metadata.get('type', 'default')
        handler = self._task_handlers.get(task_type)
        
        if not handler:
            node.state = NodeState.FAILED
            node.error = f"No handler for task type: {task_type}"
            return
        
        def run_task():
            try:
                result = handler(node)
                return TaskResult(
                    task_id=node.id,
                    success=True,
                    result=result,
                    error=None,
                    start_time=start_time,
                    end_time=datetime.now()
                )
            except Exception as e:
                return TaskResult(
                    task_id=node.id,
                    success=False,
                    result=None,
                    error=str(e),
                    start_time=start_time,
                    end_time=datetime.now()
                )
        
        future = self._executor.submit(run_task)
        self._running_tasks[node.id] = future
    
    def _wait_for_any(self) -> None:
        """等待至少一个任务完成"""
        import concurrent.futures
        
        if not self._running_tasks:
            return
        
        # 等待任意一个完成
        done, _ = concurrent.futures.wait(
            self._running_tasks.values(),
            return_when=concurrent.futures.FIRST_COMPLETED
        )
        
        # 处理完成的任务
        for future in done:
            # 找到对应的任务ID
            task_id = None
            for tid, f in self._running_tasks.items():
                if f == future:
                    task_id = tid
                    break
            
            if task_id:
                result = future.result()
                self._results[task_id] = result
                del self._running_tasks[task_id]
                
                # 更新节点状态
                node = self._graph.get_node(task_id)
                if node:
                    if result.success:
                        node.state = NodeState.COMPLETED
                        node.result = result.result
                    else:
                        node.state = NodeState.FAILED
                        node.error = result.error


# self_organizing/workflow.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from .scheduler import TaskScheduler, TaskNode
from .graph import NodeState

@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str = ""
    tasks: List[TaskNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkflowInstance:
    """工作流实例"""
    workflow_id: str
    instance_id: str
    state: str = "pending"
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)

class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, scheduler: TaskScheduler):
        self._scheduler = scheduler
        self._workflows: Dict[str, Workflow] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
    
    def register_workflow(self, workflow: Workflow) -> None:
        """注册工作流"""
        self._workflows[workflow.id] = workflow
    
    def create_instance(self, workflow_id: str, 
                        context: Dict[str, Any] = None) -> WorkflowInstance:
        """创建工作流实例"""
        import uuid
        
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            instance_id=str(uuid.uuid4())[:8],
            context=context or {}
        )
        
        self._instances[instance.instance_id] = instance
        return instance
    
    def execute(self, instance_id: str) -> Dict[str, Any]:
        """执行工作流实例"""
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")
        
        workflow = self._workflows.get(instance.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {instance.workflow_id}")
        
        instance.state = "running"
        
        # 添加任务到调度器
        for task in workflow.tasks:
            self._scheduler.add_task(task)
        
        # 执行
        results = self._scheduler.execute()
        
        # 更新实例状态
        instance.results = {r.task_id: r.result for r in results.values()}
        instance.state = "completed" if all(r.success for r in results.values()) else "failed"
        
        return instance.results
```

---

### 8. 自编译模块 (self_compiling/)

```python
"""
自编译模块 - 系统的"进化系统"

功能：
1. 自我修复：检测并修复代码问题
2. 代码生成：基于模板生成代码
3. 热加载：动态加载代码变更
4. 代码验证：验证生成的代码

遵循信任原则：
- 所有修改需要用户确认
- 修改前创建备份
- 支持回滚
"""

# self_compiling/repair.py
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import ast
import re

class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class CodeIssue:
    """代码问题"""
    file_path: str
    line_number: int
    column: int
    severity: IssueSeverity
    message: str
    issue_type: str
    suggested_fix: Optional[str] = None

@dataclass
class RepairProposal:
    """修复提案"""
    issue: CodeIssue
    original_code: str
    repaired_code: str
    confidence: float
    description: str

class CodeRepair:
    """代码修复器"""
    
    def __init__(self, audit_logger):
        self._audit = audit_logger
        self._detectors: List[Callable[[str, str], List[CodeIssue]]] = []
        self._repair_strategies: Dict[str, Callable[[CodeIssue, str], Optional[RepairProposal]]] = {}
    
    def register_detector(self, detector: Callable[[str, str], List[CodeIssue]]) -> None:
        """注册问题检测器"""
        self._detectors.append(detector)
    
    def register_repair_strategy(self, issue_type: str,
                                  strategy: Callable[[CodeIssue, str], Optional[RepairProposal]]) -> None:
        """注册修复策略"""
        self._repair_strategies[issue_type] = strategy
    
    def analyze(self, file_path: str, code: str) -> List[CodeIssue]:
        """分析代码问题"""
        issues = []
        for detector in self._detectors:
            try:
                detected = detector(file_path, code)
                issues.extend(detected)
            except Exception as e:
                print(f"Detector error: {e}")
        
        # 按严重程度排序
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
            IssueSeverity.INFO: 4
        }
        issues.sort(key=lambda i: severity_order.get(i.severity, 5))
        
        return issues
    
    def propose_repair(self, issue: CodeIssue, code: str) -> Optional[RepairProposal]:
        """提出修复方案"""
        strategy = self._repair_strategies.get(issue.issue_type)
        if strategy:
            return strategy(issue, code)
        return None
    
    def apply_repair(self, proposal: RepairProposal, 
                     confirmed: bool = False) -> bool:
        """应用修复（需要确认）"""
        if not confirmed:
            # 记录待确认的修复
            self._audit.info(
                category="self_compiling",
                action="repair.pending",
                source="CodeRepair",
                parameters={
                    'file': proposal.issue.file_path,
                    'issue_type': proposal.issue.issue_type
                }
            )
            return False
        
        # 实际应用修复...
        # 这里应该调用文件系统工具
        
        self._audit.info(
            category="self_compiling",
            action="repair.applied",
            source="CodeRepair",
            parameters={
                'file': proposal.issue.file_path,
                'issue_type': proposal.issue.issue_type
            }
        )
        
        return True


# self_compiling/generator.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from string import Template
from pathlib import Path

@dataclass
class CodeTemplate:
    """代码模板"""
    name: str
    template: str
    description: str = ""
    parameters: Dict[str, Any] = None
    
    def render(self, **kwargs) -> str:
        """渲染模板"""
        t = Template(self.template)
        return t.safe_substitute(**kwargs)

class CodeGenerator:
    """代码生成器"""
    
    def __init__(self, template_dir: str = "templates"):
        self._template_dir = Path(template_dir)
        self._templates: Dict[str, CodeTemplate] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载模板文件"""
        if not self._template_dir.exists():
            return
        
        for template_file in self._template_dir.glob("*.tpl"):
            name = template_file.stem
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._templates[name] = CodeTemplate(
                name=name,
                template=content
            )
    
    def register_template(self, template: CodeTemplate) -> None:
        """注册模板"""
        self._templates[template.name] = template
    
    def generate(self, template_name: str, 
                 output_path: str,
                 parameters: Dict[str, Any],
                 confirmed: bool = False) -> Optional[str]:
        """生成代码"""
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        code = template.render(**parameters)
        
        if not confirmed:
            # 返回预览，等待确认
            return code
        
        # 写入文件
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return code
    
    def list_templates(self) -> List[str]:
        """列出可用模板"""
        return list(self._templates.keys())


# self_compiling/hotload.py
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Set, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

class HotLoader:
    """热加载器"""
    
    def __init__(self, watch_dirs: List[str] = None):
        self._watch_dirs = watch_dirs or ['.']
        self._observer = Observer()
        self._handlers: Dict[str, Callable] = {}
        self._watched_modules: Set[str] = set()
        self._patterns = ['*.py']
        self._exclude_patterns = ['__pycache__/*', '.*']
    
    def register_handler(self, module_name: str, 
                         callback: Callable) -> None:
        """注册模块重载处理器"""
        self._handlers[module_name] = callback
    
    def start(self) -> None:
        """启动热加载监控"""
        event_handler = _HotReloadHandler(self)
        
        for watch_dir in self._watch_dirs:
            path = Path(watch_dir).resolve()
            if path.exists():
                self._observer.schedule(event_handler, str(path), recursive=True)
        
        self._observer.start()
    
    def stop(self) -> None:
        """停止热加载监控"""
        self._observer.stop()
        self._observer.join()
    
    def reload_module(self, module_name: str) -> bool:
        """重新加载模块"""
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                
                # 调用处理器
                if module_name in self._handlers:
                    self._handlers[module_name]()
                
                return True
        except Exception as e:
            print(f"Failed to reload {module_name}: {e}")
        
        return False

class _HotReloadHandler(FileSystemEventHandler):
    """文件变更处理器"""
    
    def __init__(self, loader: HotLoader):
        self._loader = loader
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # 检查是否是Python文件
        if file_path.suffix != '.py':
            return
        
        # 排除特定目录
        if '__pycache__' in str(file_path):
            return
        
        # 计算模块名
        module_name = self._get_module_name(file_path)
        
        if module_name:
            print(f"Detected change in {module_name}, reloading...")
            self._loader.reload_module(module_name)
    
    def _get_module_name(self, file_path: Path) -> Optional[str]:
        """从文件路径获取模块名"""
        # 简化实现
        for module_name in self._loader._handlers:
            if module_name in str(file_path):
                return module_name
        return None
```

---

## 模块间数据流和控制流

### 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           四自系统数据流                                  │
└─────────────────────────────────────────────────────────────────────────┘

                         ┌──────────────┐
                         │   配置系统    │
                         │   Config     │
                         └──────┬───────┘
                                │ 配置数据
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  自感知模块   │      │  自适应模块   │      │  自组织模块   │
│SelfAwareness │      │SelfAdaptive  │      │SelfOrganizing│
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       │ 指标数据            │ 调优指令            │ 任务指令
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────┐
│                    事件总线 EventBus                      │
│              （模块间解耦通信）                            │
└─────────────────────────────────────────────────────────┘
       │                     │                     │
       │                     │                     │
       ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  审计系统     │      │  持久化系统   │      │  自编译模块   │
│   Audit      │      │ Persistence  │      │SelfCompiling │
└──────────────┘      └──────────────┘      └──────────────┘
```

### 控制流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           四自系统控制流                                  │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌─────────┐
                              │  启动   │
                              └────┬────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │      初始化配置系统        │
                    │   ConfigManager.load()   │
                    └────────────┬─────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │ 初始化审计   │  │ 初始化持久化 │  │ 初始化事件   │
       │   系统      │  │    系统     │  │    总线     │
       └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
              ┌──────────────────────────────────┐
              │        初始化四自模块              │
              │  ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
              │  │自感知│ │自适应│ │自组织│ │自编译│   │
              │  └────┘ └────┘ └────┘ └────┘   │
              └──────────────────────────────────┘
                               │
                               ▼
                    ┌────────────────────┐
                    │    启动主循环       │
                    │   Main Loop        │
                    └────────────────────┘
```

---

## 系统集成

### 主入口 (temper.py)

```python
#!/usr/bin/env python3
"""
🧊 Temper Evolve v3.0 - 四自系统版

AI 原生 Coding Agent，具备自感知、自适应、自组织、自编译能力
"""

import os
import sys
import signal
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# 核心组件
from temper.core.result import ok, err, is_ok, unwrap
from temper.core.events import event_bus, Event, EventType

# 基础设施
from temper.config.manager import ConfigManager
from temper.audit.logger import AuditLogger, AuditCategory
from temper.audit.tracer import OperationTracer
from temper.persistence.manager import PersistenceManager

# 四自模块
from temper.self_awareness.monitor import SystemMonitor
from temper.self_awareness.metrics import MetricsCollector
from temper.self_awareness.diagnostics import Diagnostics
from temper.self_adaptive.tuner import ParameterTuner
from temper.self_adaptive.strategies import StrategyEngine
from temper.self_organizing.workflow import WorkflowEngine
from temper.self_organizing.scheduler import TaskScheduler
from temper.self_compiling.repair import CodeRepair
from temper.self_compiling.generator import CodeGenerator
from temper.self_compiling.hotload import HotLoader

# 加载环境变量
load_dotenv()

class TemperSystem:
    """Temper 系统主类"""
    
    def __init__(self):
        self._running = False
        
        # 基础设施
        self.config: ConfigManager = None
        self.audit: AuditLogger = None
        self.tracer: OperationTracer = None
        self.persistence: PersistenceManager = None
        
        # 四自模块
        self.metrics: MetricsCollector = None
        self.monitor: SystemMonitor = None
        self.diagnostics: Diagnostics = None
        self.tuner: ParameterTuner = None
        self.strategy_engine: StrategyEngine = None
        self.workflow_engine: WorkflowEngine = None
        self.code_repair: CodeRepair = None
        self.code_generator: CodeGenerator = None
        self.hot_loader: HotLoader = None
    
    def initialize(self) -> bool:
        """初始化系统"""
        print("🚀 初始化 Temper 系统...")
        
        # 1. 初始化配置系统
        self.config = ConfigManager()
        result = self.config.load()
        if not is_ok(result):
            print(f"❌ 配置加载失败: {result}")
            return False
        print("✅ 配置系统初始化完成")
        
        config = self.config.get()
        
        # 2. 初始化审计系统
        self.audit = AuditLogger(config.audit.storage_dir)
        self.tracer = OperationTracer(self.audit)
        print("✅ 审计系统初始化完成")
        
        # 3. 初始化持久化系统
        self.persistence = PersistenceManager(config.persistence.storage_dir)
        print("✅ 持久化系统初始化完成")
        
        # 4. 初始化自感知模块
        if config.self_awareness.enabled:
            self.metrics = MetricsCollector()
            self.monitor = SystemMonitor(self.metrics)
            self.diagnostics = Diagnostics()
            self.metrics.start_collection(config.self_awareness.metrics_collection_interval)
            print("✅ 自感知模块初始化完成")
        
        # 5. 初始化自适应模块
        if config.self_adaptive.enabled:
            self.tuner = ParameterTuner(self.metrics)
            self.strategy_engine = StrategyEngine(self.metrics, self.tuner)
            print("✅ 自适应模块初始化完成")
        
        # 6. 初始化自组织模块
        if config.self_organizing.enabled:
            scheduler = TaskScheduler(config.self_organizing.max_concurrent_tasks)
            self.workflow_engine = WorkflowEngine(scheduler)
            print("✅ 自组织模块初始化完成")
        
        # 7. 初始化自编译模块
        if config.self_compiling.enabled:
            self.code_repair = CodeRepair(self.audit)
            self.code_generator = CodeGenerator(config.self_compiling.generation.get('template_dir'))
            self.hot_loader = HotLoader()
            print("✅ 自编译模块初始化完成")
        
        # 8. 启动事件总线
        event_bus.start()
        print("✅ 事件总线启动完成")
        
        # 9. 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 10. 恢复状态
        self._restore_state()
        
        # 记录启动事件
        self.audit.info(
            category=AuditCategory.SYSTEM,
            action="system.start",
            source="TemperSystem"
        )
        
        print("\n🧊 Temper 系统初始化完成！")
        return True
    
    def _restore_state(self) -> None:
        """恢复系统状态"""
        # 从持久化存储恢复
        pass
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n🛑 收到终止信号，正在关闭...")
        self.shutdown()
        sys.exit(0)
    
    def run(self) -> None:
        """运行主循环"""
        self._running = True
        
        print("\n" + "=" * 50)
        print("🧊 Temper Evolve v3.0 - 四自系统")
        print("=" * 50)
        print()
        print("命令:")
        print("  /status  - 查看系统状态")
        print("  /metrics - 查看系统指标")
        print("  /config  - 查看/修改配置")
        print("  /audit   - 查看审计日志")
        print("  /repair  - 代码修复")
        print("  /clear   - 清空对话历史")
        print("  exit     - 退出")
        print()
        
        while self._running:
            try:
                user_input = input("👤 你: ").strip()
                
                if user_input.lower() == 'exit':
                    break
                
                if user_input.lower() == '/status':
                    self._show_status()
                    continue
                
                if user_input.lower() == '/metrics':
                    self._show_metrics()
                    continue
                
                if user_input.lower().startswith('/config'):
                    self._handle_config(user_input)
                    continue
                
                # 处理其他命令...
                
                if user_input:
                    self._process_input(user_input)
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        self.shutdown()
    
    def _show_status(self) -> None:
        """显示系统状态"""
        print("\n📊 系统状态:")
        if self.diagnostics:
            status = self.diagnostics.get_overall_status()
            print(f"  健康状态: {status.value}")
        print()
    
    def _show_metrics(self) -> None:
        """显示系统指标"""
        print("\n📈 系统指标:")
        if self.metrics:
            recent = self.metrics.get_history(limit=5)
            for m in recent:
                print(f"  {m.name}: {m.value}{m.unit}")
        print()
    
    def _handle_config(self, command: str) -> None:
        """处理配置命令"""
        parts = command.split()
        if len(parts) == 1:
            # 显示配置
            import json
            config_dict = self.config._config_to_dict(self.config.get())
            print("\n⚙️ 当前配置:")
            print(json.dumps(config_dict, indent=2, ensure_ascii=False))
        elif len(parts) == 3:
            # 修改配置: /config path value
            path = parts[1]
            value = parts[2]
            result = self.config.update(path, value)
            if is_ok(result):
                print(f"✅ 配置已更新: {path} = {value}")
            else:
                print(f"❌ 配置更新失败: {result}")
        print()
    
    def _process_input(self, user_input: str) -> None:
        """处理用户输入"""
        # 使用 tracer 追踪操作
        with self.tracer.trace(
            category=AuditCategory.USER_ACTION,
            action="chat",
            source="TemperSystem",
            parameters={'input': user_input[:100]}
        ):
            # 调用 AI 处理
            print(f"🤖 处理中: {user_input[:50]}...")
    
    def shutdown(self) -> None:
        """关闭系统"""
        print("\n🛑 正在关闭系统...")
        
        # 保存状态
        if self.persistence:
            self.persistence.save_all()
        
        # 停止模块
        if self.metrics:
            self.metrics.stop_collection()
        
        if self.hot_loader:
            self.hot_loader.stop()
        
        # 停止事件总线
        event_bus.stop()
        
        # 关闭审计日志
        if self.audit:
            self.audit.info(
                category=AuditCategory.SYSTEM,
                action="system.stop",
                source="TemperSystem"
            )
            self.audit.close()
        
        print("👋 系统已安全关闭")


def main():
    """主入口"""
    system = TemperSystem()
    
    if not system.initialize():
        print("❌ 系统初始化失败")
        sys.exit(1)
    
    system.run()


if __name__ == "__main__":
    main()
```

---

## 配置示例 (defaults.yaml)

```yaml
# Temper 系统默认配置

system:
  name: "temper"
  version: "3.0.0"
  log_level: "info"
  max_workers: 4

self_awareness:
  enabled: true
  health_check_interval: 30
  metrics_collection_interval: 10
  alert_thresholds:
    cpu_percent: 80.0
    memory_percent: 85.0
    disk_percent: 90.0
    response_time_ms: 5000
  retention_days: 7

self_adaptive:
  enabled: true
  tuning_interval: 300
  optimization_enabled: true
  load_balance_enabled: true
  auto_scale: false
  tuning_params:
    temperature_range: [0.1, 1.0]
    max_tokens_range: [1024, 8192]
    learning_rate: 0.01

self_organizing:
  enabled: true
  max_concurrent_tasks: 10
  task_timeout: 300
  retry_attempts: 3
  retry_delay: 5
  workflow_defaults:
    parallel_limit: 5
    dependency_resolution: "automatic"

self_compiling:
  enabled: true
  auto_repair: false
  auto_generate: false
  hotload_enabled: true
  generation:
    template_dir: "templates"
    output_dir: "generated"
    validation_enabled: true
  hotload:
    watch_patterns:
      - "*.py"
    exclude_patterns:
      - "__pycache__/*"
    cooldown_seconds: 2

audit:
  enabled: true
  log_level: "info"
  storage_type: "file"
  retention_days: 30
  max_file_size_mb: 100

persistence:
  enabled: true
  storage_dir: "data"
  auto_save_interval: 60
  snapshot_interval: 3600
  max_snapshots: 10
```

---

## 总结

本架构设计文档为"四自系统"提供了完整的实现方案：

### 核心特点

1. **模块化设计**：每个模块职责清晰，通过事件总线解耦
2. **配置驱动**：所有行为通过配置控制，支持热重载
3. **审计追踪**：所有操作可追溯，支持回放
4. **持久化支持**：状态自动保存和恢复
5. **扩展性强**：插件化设计，易于扩展

### 铁三角原则实现

| 原则 | 实现方式 |
|------|----------|
| 信任原则 | 审计系统记录所有操作，代码修复需用户确认 |
| 复利原则 | 持久化系统保存状态，支持快照和回滚 |
| 杠杆原则 | 配置系统驱动所有行为，拒绝硬编码 |

### 后续工作

1. 实现各模块的具体功能
2. 编写单元测试和集成测试
3. 完善文档和示例
4. 性能优化和调优
