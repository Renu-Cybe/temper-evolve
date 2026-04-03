"""
心跳循环模块

让 Temper 系统真正"活"起来：
- 定时自检（自感知）
- 自适应调整（自适应）
- 工作流执行（自组织）
- 代码自修复（自编译）

事件驱动增强：
- 所有四自操作发布事件
- 事件链接到审计和持久化系统
"""

from .evolver import TemperEvolver, EvolverConfig, register_evolver_event_handlers

__all__ = ['TemperEvolver', 'EvolverConfig', 'register_evolver_event_handlers']