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

from .repair import CodeRepair, CodeIssue, IssueSeverity, RepairProposal
from .generator import CodeGenerator, CodeTemplate

__all__ = [
    'CodeRepair', 'CodeIssue', 'IssueSeverity', 'RepairProposal',
    'CodeGenerator', 'CodeTemplate',
]
