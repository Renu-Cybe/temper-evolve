"""
自组织模块 - 系统的"协调系统"

功能：
1. 工作流合成：动态组合任务流程
2. 任务编排：管理任务执行顺序
3. 依赖管理：解析和处理任务依赖
4. 调度优化：优化任务调度策略
"""

from .graph import DependencyGraph, TaskNode, NodeState
from .scheduler import TaskScheduler, TaskResult
from .workflow import Workflow, WorkflowInstance, WorkflowEngine

__all__ = [
    'DependencyGraph', 'TaskNode', 'NodeState',
    'TaskScheduler', 'TaskResult',
    'Workflow', 'WorkflowInstance', 'WorkflowEngine',
]
