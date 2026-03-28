"""记忆系统工具 - 供 Agent 调用"""
from typing import Dict, List, Optional, Any

from .manager import MemoryManager
from .types import MemoryType


class MemoryTools:
    """记忆工具集 - 封装为工具调用接口"""
    
    def __init__(self, manager: Optional[MemoryManager] = None):
        self.manager = manager or MemoryManager()
    
    # ========== 工具函数 ==========
    
    def remember(self, content: str, 
                 memory_type: str = "message",
                 importance: float = 1.0) -> Dict:
        """
        记住一条信息
        
        Args:
            content: 要记忆的内容
            memory_type: 类型 (message/fact/code/error/decision/project)
            importance: 重要性 0.0-2.0
        """
        try:
            mtype = MemoryType(memory_type)
        except ValueError:
            mtype = MemoryType.MESSAGE
        
        memory_id = self.manager.remember(
            content=content,
            memory_type=mtype,
            importance=importance
        )
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"已记住: {content[:50]}..."
        }
    
    def recall(self, query: str, 
               memory_type: Optional[str] = None,
               limit: int = 5) -> Dict:
        """
        回忆相关信息
        
        Args:
            query: 搜索关键词
            memory_type: 可选的类型过滤
            limit: 返回数量
        """
        mtype = None
        if memory_type:
            try:
                mtype = MemoryType(memory_type)
            except ValueError:
                pass
        
        memories = self.manager.recall(query, mtype, limit)
        
        results = []
        for m in memories:
            results.append({
                "id": m.id,
                "type": m.type.value,
                "content": m.content[:300],
                "timestamp": m.timestamp.isoformat(),
                "importance": m.importance
            })
        
        return {
            "success": True,
            "count": len(results),
            "memories": results
        }
    
    def recall_recent(self, hours: int = 24, limit: int = 10) -> Dict:
        """
        回忆最近的信息
        
        Args:
            hours: 最近多少小时
            limit: 返回数量
        """
        memories = self.manager.recall_recent(hours, limit=limit)
        
        results = []
        for m in memories:
            results.append({
                "type": m.type.value,
                "content": m.content[:200],
                "time": m.timestamp.strftime("%H:%M")
            })
        
        return {
            "success": True,
            "period": f"最近{hours}小时",
            "memories": results
        }
    
    def remember_fact(self, fact: str, category: Optional[str] = None) -> Dict:
        """
        记住关键事实
        
        Args:
            fact: 事实内容
            category: 分类标签
        """
        self.manager.remember_fact(fact, category)
        return {
            "success": True,
            "message": f"已记录事实: {fact[:50]}..."
        }
    
    def remember_error(self, error: str, 
                       solution: Optional[str] = None) -> Dict:
        """
        记住错误和解决方案
        
        Args:
            error: 错误描述
            solution: 解决方案
        """
        self.manager.remember_error(error, solution)
        return {
            "success": True,
            "message": "已记录错误信息"
        }
    
    def get_project_context(self, project_name: Optional[str] = None) -> Dict:
        """
        获取项目上下文
        
        Args:
            project_name: 项目名称，None则使用当前项目
        """
        if project_name is None:
            # 从当前会话获取
            session = self.manager.store.get_current_session()
            if session:
                project_name = session.project
        
        if not project_name:
            return {
                "success": False,
                "message": "未指定项目"
            }
        
        context = self.manager.get_project_context(project_name)
        if not context:
            return {
                "success": False,
                "message": f"项目 {project_name} 不存在"
            }
        
        return {
            "success": True,
            "project": context.to_dict()
        }
    
    def init_project(self, name: str, path: str,
                     description: Optional[str] = None,
                     tech_stack: Optional[List[str]] = None) -> Dict:
        """
        初始化项目
        
        Args:
            name: 项目名称
            path: 项目路径
            description: 项目描述
            tech_stack: 技术栈列表
        """
        context = self.manager.init_project(
            name=name,
            path=path,
            description=description,
            tech_stack=tech_stack
        )
        
        return {
            "success": True,
            "message": f"项目 {name} 已初始化",
            "project": context.to_dict()
        }
    
    def list_projects(self) -> Dict:
        """列出所有项目"""
        projects = self.manager.list_projects()
        return {
            "success": True,
            "projects": projects,
            "count": len(projects)
        }
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        return self.manager.get_stats()
    
    def build_context_for_prompt(self, 
                                  query: Optional[str] = None,
                                  max_tokens: int = 3000) -> str:
        """
        构建上下文用于提示注入
        
        这是内部方法，返回格式化的上下文字符串
        """
        return self.manager.build_context(query, max_tokens)
    
    def get_current_session(self) -> Dict:
        """获取当前会话信息"""
        session = self.manager.store.get_current_session()
        if not session:
            return {
                "success": False,
                "message": "没有活跃会话"
            }
        
        return {
            "success": True,
            "session_id": session.id,
            "project": session.project,
            "start_time": session.start_time.isoformat(),
            "message_count": len(session.messages)
        }
    
    def switch_session(self, project_name: Optional[str] = None) -> Dict:
        """
        切换/开始新会话
        
        Args:
            project_name: 关联的项目名
        """
        # 结束当前会话
        self.manager.end_session()
        
        # 开始新会话
        session_id = self.manager.start_session(project_name)
        
        return {
            "success": True,
            "session_id": session_id,
            "project": project_name,
            "message": f"新会话已启动: {session_id}"
        }


# 全局实例（单例模式）
_memory_tools: Optional[MemoryTools] = None


def get_memory_tools() -> MemoryTools:
    """获取记忆工具实例"""
    global _memory_tools
    if _memory_tools is None:
        _memory_tools = MemoryTools()
    return _memory_tools
