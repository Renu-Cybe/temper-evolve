"""
配置模式定义

定义所有配置项的数据结构和默认值
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "temper"
    version: str = "3.0.0"
    log_level: LogLevel = LogLevel.INFO
    max_workers: int = 4
    debug_mode: bool = False


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
    enable_detailed_metrics: bool = True


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
    
    # 策略配置
    strategies: List[Dict[str, Any]] = field(default_factory=list)


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
        'dependency_resolution': 'automatic',
        'fail_fast': True
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
        'validation_enabled': True,
        'backup_before_write': True
    })
    
    # 热加载配置
    hotload: Dict[str, Any] = field(default_factory=lambda: {
        'watch_patterns': ['*.py'],
        'exclude_patterns': ['__pycache__/*', '*.pyc'],
        'cooldown_seconds': 2
    })


@dataclass
class AuditConfig:
    """审计配置"""
    enabled: bool = True
    log_level: str = "info"
    storage_type: str = "file"                # file, database
    storage_dir: str = "data/audit"
    retention_days: int = 30
    max_file_size_mb: int = 100
    enable_console_output: bool = False


@dataclass
class PersistenceConfig:
    """持久化配置"""
    enabled: bool = True
    storage_dir: str = "data"
    auto_save_interval: int = 60              # 秒
    snapshot_interval: int = 3600             # 秒
    max_snapshots: int = 10
    compression_enabled: bool = True


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
    
    def to_dict(self) -> dict:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        """从字典创建配置"""
        # 递归转换嵌套字典为配置对象
        def convert_section(section_class, data_dict):
            if not data_dict:
                return section_class()
            valid_fields = {f.name for f in section_class.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data_dict.items() if k in valid_fields}
            return section_class(**filtered)
        
        return cls(
            system=convert_section(SystemConfig, data.get('system')),
            self_awareness=convert_section(SelfAwarenessConfig, data.get('self_awareness')),
            self_adaptive=convert_section(SelfAdaptiveConfig, data.get('self_adaptive')),
            self_organizing=convert_section(SelfOrganizingConfig, data.get('self_organizing')),
            self_compiling=convert_section(SelfCompilingConfig, data.get('self_compiling')),
            audit=convert_section(AuditConfig, data.get('audit')),
            persistence=convert_section(PersistenceConfig, data.get('persistence')),
            custom=data.get('custom', {})
        )
