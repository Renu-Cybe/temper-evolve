"""
配置系统 - 杠杆原则的核心实现

设计原则：
1. 配置驱动：所有行为通过配置控制
2. 分层配置：默认 < 文件 < 环境变量 < 运行时
3. 类型安全：配置项有明确的类型和验证
4. 热重载：支持配置动态更新
"""

from .schema import (
    Config, SystemConfig, SelfAwarenessConfig,
    SelfAdaptiveConfig, SelfOrganizingConfig, SelfCompilingConfig,
    AuditConfig, PersistenceConfig, LogLevel
)

from .manager import ConfigManager

__all__ = [
    'Config', 'ConfigManager',
    'SystemConfig', 'SelfAwarenessConfig',
    'SelfAdaptiveConfig', 'SelfOrganizingConfig',
    'SelfCompilingConfig', 'AuditConfig', 'PersistenceConfig',
    'LogLevel',
]
