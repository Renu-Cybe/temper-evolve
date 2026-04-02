"""
依赖图

管理任务间的依赖关系
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from enum import Enum


class NodeState(Enum):
    """节点状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    SKIPPED = "skipped"       # 已跳过
    CANCELLED = "cancelled"   # 已取消


@dataclass
class TaskNode:
    """任务节点
    
    Attributes:
        id: 节点唯一标识
        name: 节点名称
        dependencies: 依赖的节点ID集合
        state: 当前状态
        result: 执行结果
        error: 错误信息
        metadata: 额外元数据
        priority: 优先级（数字越大优先级越高）
        timeout_seconds: 超时时间（秒）
        retry_count: 重试次数
    """
    id: str
    name: str
    dependencies: Set[str] = field(default_factory=set)
    state: NodeState = NodeState.PENDING
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'dependencies': list(self.dependencies),
            'state': self.state.value,
            'result': self.result,
            'error': self.error,
            'priority': self.priority,
            'retry_count': self.retry_count
        }
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retries


class DependencyGraph:
    """依赖图
    
    管理任务节点及其依赖关系
    
    使用示例：
        graph = DependencyGraph()
        
        # 添加节点
        graph.add_node(TaskNode("A", "Task A"))
        graph.add_node(TaskNode("B", "Task B", dependencies={"A"}))
        graph.add_node(TaskNode("C", "Task C", dependencies={"A"}))
        
        # 检查循环依赖
        if graph.detect_cycles():
            print("Circular dependency detected!")
        
        # 拓扑排序
        order = graph.topological_sort()
        
        # 获取就绪节点
        ready = graph.get_ready_nodes()
    """
    
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
    
    def remove_node(self, node_id: str) -> bool:
        """移除节点"""
        if node_id not in self._nodes:
            return False
        
        # 移除依赖关系
        for dep_id in self._nodes[node_id].dependencies:
            if dep_id in self._edges:
                self._edges[dep_id].discard(node_id)
        
        # 从其他节点的依赖中移除
        for node in self._nodes.values():
            node.dependencies.discard(node_id)
        
        del self._nodes[node_id]
        del self._edges[node_id]
        
        return True
    
    def get_node(self, node_id: str) -> Optional[TaskNode]:
        """获取节点"""
        return self._nodes.get(node_id)
    
    def has_node(self, node_id: str) -> bool:
        """检查节点是否存在"""
        return node_id in self._nodes
    
    def get_ready_nodes(self) -> List[TaskNode]:
        """获取就绪节点（依赖已满足）
        
        Returns:
            就绪节点列表（按优先级排序）
        """
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
        
        # 按优先级排序
        ready.sort(key=lambda n: n.priority, reverse=True)
        
        return ready
    
    def get_dependents(self, node_id: str) -> Set[str]:
        """获取依赖该节点的所有节点"""
        return self._edges.get(node_id, set())
    
    def get_dependencies(self, node_id: str) -> Set[str]:
        """获取节点的所有依赖"""
        node = self._nodes.get(node_id)
        return node.dependencies if node else set()
    
    def topological_sort(self) -> List[str]:
        """拓扑排序
        
        Returns:
            节点ID的有序列表
            
        Raises:
            ValueError: 如果存在循环依赖
        """
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
        """检测循环依赖
        
        Returns:
            循环依赖的节点列表，无循环返回 None
        """
        try:
            self.topological_sort()
            return None
        except ValueError as e:
            # 解析错误信息获取循环节点
            msg = str(e)
            if "Circular dependency detected at" in msg:
                cycle_start = msg.split("at ")[-1]
                return self._find_cycle_path(cycle_start)
            return None
    
    def _find_cycle_path(self, start_node: str) -> List[str]:
        """查找循环路径"""
        path = []
        visited = set()
        
        def dfs(node_id: str) -> bool:
            if node_id in visited:
                if node_id == start_node:
                    path.append(node_id)
                    return True
                return False
            
            visited.add(node_id)
            path.append(node_id)
            
            node = self._nodes.get(node_id)
            if node:
                for dep_id in node.dependencies:
                    if dfs(dep_id):
                        return True
            
            path.pop()
            return False
        
        dfs(start_node)
        return path
    
    def get_all_nodes(self) -> List[TaskNode]:
        """获取所有节点"""
        return list(self._nodes.values())
    
    def get_node_count(self) -> int:
        """获取节点数量"""
        return len(self._nodes)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        states = {}
        for node in self._nodes.values():
            state = node.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            'total_nodes': len(self._nodes),
            'states': states
        }
    
    def reset_all_states(self) -> None:
        """重置所有节点状态为 PENDING"""
        for node in self._nodes.values():
            node.state = NodeState.PENDING
            node.result = None
            node.error = None
            node.retry_count = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'nodes': [node.to_dict() for node in self._nodes.values()],
            'edges': {k: list(v) for k, v in self._edges.items()}
        }
