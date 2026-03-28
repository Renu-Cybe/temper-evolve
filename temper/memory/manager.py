"""记忆管理器 - 高层 API"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable

from .types import Memory, MemoryType, Session, ProjectContext
from .store import MemoryStore


class MemoryManager:
    """记忆管理器 - 提供简洁的记忆操作接口"""
    
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self._summarizer: Optional[Callable[[List[Memory]], str]] = None
    
    # ========== 会话生命周期 ==========
    
    def start_session(self, project: Optional[str] = None) -> str:
        """开始新会话"""
        session = self.store.create_session(project)
        
        # 记录会话开始
        self.remember(
            content=f"会话开始{' - 项目: ' + project if project else ''}",
            memory_type=MemoryType.SUMMARY,
            importance=0.5
        )
        
        return session.id
    
    def end_session(self, generate_summary: bool = True):
        """结束当前会话"""
        session = self.store.get_current_session()
        if not session:
            return
        
        summary = None
        if generate_summary and self._summarizer:
            summary = self._summarizer(session.messages)
        
        self.store.end_session(summary)
    
    def get_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        session = self.store.get_current_session()
        return session.id if session else None
    
    # ========== 核心记忆操作 ==========
    
    def remember(self, 
                 content: str,
                 memory_type: MemoryType = MemoryType.MESSAGE,
                 importance: float = 1.0,
                 metadata: Optional[Dict] = None) -> str:
        """
        记住一条信息
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性 (0.0-2.0)，越高越不容易被清理
            metadata: 额外元数据
        """
        session = self.store.get_current_session()
        
        memory = Memory(
            id=str(uuid.uuid4())[:12],
            type=memory_type,
            content=content,
            timestamp=datetime.now(),
            session_id=session.id if session else None,
            project=session.project if session else None,
            metadata=metadata or {},
            importance=importance
        )
        
        return self.store.save_memory(memory)
    
    def recall(self, 
               query: str,
               memory_type: Optional[MemoryType] = None,
               limit: int = 10) -> List[Memory]:
        """
        回忆相关信息
        
        Args:
            query: 搜索关键词
            memory_type: 限定记忆类型
            limit: 返回数量
        """
        return self.store.search_memories(
            query=query,
            memory_type=memory_type,
            limit=limit
        )
    
    def recall_recent(self, 
                      hours: int = 24,
                      memory_type: Optional[MemoryType] = None) -> List[Memory]:
        """回忆最近的信息"""
        since = datetime.now() - timedelta(hours=hours)
        return self.store.search_memories(
            since=since,
            memory_type=memory_type,
            limit=50
        )
    
    def recall_session(self, session_id: Optional[str] = None) -> List[Memory]:
        """回忆特定会话的内容"""
        if session_id is None:
            session = self.store.get_current_session()
            if session:
                session_id = session.id
        
        if session_id:
            return self.store.search_memories(session_id=session_id, limit=1000)
        return []
    
    def recall_project(self, 
                       project_name: Optional[str] = None,
                       limit: int = 50) -> List[Memory]:
        """回忆项目相关信息"""
        if project_name is None:
            session = self.store.get_current_session()
            if session:
                project_name = session.project
        
        if project_name:
            return self.store.search_memories(project=project_name, limit=limit)
        return []
    
    # ========== 项目上下文 ==========
    
    def init_project(self, 
                     name: str,
                     path: str,
                     description: Optional[str] = None,
                     tech_stack: Optional[List[str]] = None) -> ProjectContext:
        """初始化项目上下文"""
        context = ProjectContext(
            name=name,
            path=path,
            description=description,
            tech_stack=tech_stack or []
        )
        self.store.save_project_context(context)
        
        # 记录项目初始化
        self.remember(
            content=f"初始化项目: {name}\n路径: {path}\n描述: {description}",
            memory_type=MemoryType.PROJECT,
            importance=1.5,
            metadata={"project_name": name, "path": path}
        )
        
        return context
    
    def get_project_context(self, name: str) -> Optional[ProjectContext]:
        """获取项目上下文"""
        return self.store.load_project_context(name)
    
    def update_project_convention(self, 
                                   project_name: str,
                                   key: str,
                                   value: str):
        """更新项目约定"""
        context = self.store.load_project_context(project_name)
        if context:
            context.conventions[key] = value
            context.last_accessed = datetime.now()
            self.store.save_project_context(context)
            
            self.remember(
                content=f"项目 {project_name} 约定: {key} = {value}",
                memory_type=MemoryType.PROJECT,
                importance=1.2
            )
    
    def switch_project(self, project_name: str) -> bool:
        """切换到项目上下文"""
        context = self.store.load_project_context(project_name)
        if context:
            # 更新最后访问时间
            context.last_accessed = datetime.now()
            self.store.save_project_context(context)
            
            # 如果当前有会话，切换到该项目
            session = self.store.get_current_session()
            if session:
                session.project = project_name
            
            return True
        return False
    
    # ========== 智能记忆 ==========
    
    def remember_fact(self, fact: str, category: Optional[str] = None):
        """记住关键事实"""
        self.remember(
            content=fact,
            memory_type=MemoryType.FACT,
            importance=1.5,  # 事实重要性较高
            metadata={"category": category} if category else {}
        )
    
    def remember_code(self, 
                      code: str,
                      description: str,
                      language: Optional[str] = None):
        """记住代码片段"""
        self.remember(
            content=f"{description}\n```{language or ''}\n{code}\n```",
            memory_type=MemoryType.CODE,
            importance=1.3,
            metadata={"language": language, "description": description}
        )
    
    def remember_error(self, 
                       error: str,
                       solution: Optional[str] = None,
                       context: Optional[str] = None):
        """记住错误和解决方案"""
        content = f"错误: {error}"
        if context:
            content += f"\n上下文: {context}"
        if solution:
            content += f"\n解决方案: {solution}"
        
        self.remember(
            content=content,
            memory_type=MemoryType.ERROR,
            importance=1.4,  # 错误记录很重要
            metadata={"has_solution": solution is not None}
        )
    
    def remember_decision(self, 
                          decision: str,
                          reasoning: str,
                          alternatives: Optional[List[str]] = None):
        """记住决策过程"""
        content = f"决策: {decision}\n理由: {reasoning}"
        if alternatives:
            content += f"\n备选方案: {', '.join(alternatives)}"
        
        self.remember(
            content=content,
            memory_type=MemoryType.DECISION,
            importance=1.3
        )
    
    # ========== 上下文构建 ==========
    
    def build_context(self, 
                      query: Optional[str] = None,
                      max_tokens: int = 4000) -> str:
        """
        构建当前上下文字符串，用于注入到提示中
        
        策略:
        1. 当前项目上下文
        2. 相关历史记忆
        3. 最近会话摘要
        """
        parts = []
        
        # 1. 项目上下文
        session = self.store.get_current_session()
        if session and session.project:
            project_ctx = self.store.load_project_context(session.project)
            if project_ctx:
                parts.append(f"## 当前项目: {project_ctx.name}")
                if project_ctx.description:
                    parts.append(f"描述: {project_ctx.description}")
                if project_ctx.tech_stack:
                    parts.append(f"技术栈: {', '.join(project_ctx.tech_stack)}")
                if project_ctx.conventions:
                    parts.append("约定:")
                    for k, v in project_ctx.conventions.items():
                        parts.append(f"  - {k}: {v}")
                parts.append("")
        
        # 2. 相关记忆
        if query:
            relevant = self.recall(query, limit=5)
            if relevant:
                parts.append("## 相关历史")
                for m in relevant:
                    parts.append(f"- [{m.type.value}] {m.content[:200]}...")
                parts.append("")
        
        # 3. 最近会话
        recent = self.recall_recent(hours=24, limit=10)
        if recent:
            parts.append("## 今日工作")
            for m in recent[-5:]:  # 最近5条
                parts.append(f"- {m.content[:150]}...")
        
        context = "\n".join(parts)
        
        # 简单的 token 估算（中文约1.5字符/token，英文约4字符/token）
        # 这里简化处理
        if len(context) > max_tokens * 3:
            context = context[:max_tokens * 3] + "\n... (上下文已截断)"
        
        return context
    
    # ========== 统计与维护 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        return self.store.get_stats()
    
    def list_projects(self) -> List[str]:
        """列出所有项目"""
        return self.store.list_projects()
    
    def list_sessions(self, limit: int = 10) -> List[Session]:
        """列出历史会话"""
        return self.store.list_sessions(limit=limit)
    
    def cleanup(self, days: int = 30):
        """清理旧记忆"""
        count = self.store.cleanup_old_memories(days)
        return count
    
    def set_summarizer(self, fn: Callable[[List[Memory]], str]):
        """设置摘要生成函数"""
        self._summarizer = fn
    
    def close(self):
        """关闭管理器"""
        self.store.close()
