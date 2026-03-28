"""
Temper Memory System - 持久化记忆增强

三层记忆架构:
- Working: 当前会话上下文
- Short-term: 近期会话摘要  
- Long-term: 关键事实和项目知识

快速开始:
    from temper.memory import MemoryManager
    
    memory = MemoryManager()
    memory.start_session(project="my_project")
    
    # 记住信息
    memory.remember("用户喜欢使用 FastAPI", importance=1.5)
    memory.remember_fact("项目使用 PostgreSQL", category="database")
    
    # 回忆信息
    results = memory.recall("FastAPI")
    recent = memory.recall_recent(hours=24)
    
    # 项目上下文
    memory.init_project("my_api", "/path/to/project",
                       tech_stack=["FastAPI", "PostgreSQL"])
"""

from .manager import MemoryManager
from .types import Memory, MemoryType, Session, ProjectContext
from .store import MemoryStore
from .tools import MemoryTools, get_memory_tools

__all__ = [
    'MemoryManager',
    'Memory', 
    'MemoryType',
    'Session',
    'ProjectContext',
    'MemoryStore',
    'MemoryTools',
    'get_memory_tools'
]

# 版本
__version__ = "1.0.0"
