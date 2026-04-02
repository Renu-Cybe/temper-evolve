"""
审计系统 - 信任原则的核心实现

设计原则：
1. 透明可审计：所有操作记录可追溯
2. 不可篡改：审计日志防篡改（通过哈希链）
3. 可回放：支持操作回放
4. 结构化：统一的审计记录格式
"""

from .logger import AuditLogger, AuditLevel, AuditCategory, AuditRecord
from .tracer import OperationTracer

__all__ = [
    'AuditLogger', 'AuditLevel', 'AuditCategory', 'AuditRecord',
    'OperationTracer',
]
