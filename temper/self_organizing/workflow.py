"""
工作流引擎

管理和执行工作流
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from .scheduler import TaskScheduler, TaskNode, TaskResult
from .graph import NodeState
import uuid


@dataclass
class Workflow:
    """工作流定义
    
    Attributes:
        id: 工作流ID
        name: 工作流名称
        description: 描述
        tasks: 任务列表
        metadata: 额外元数据
        version: 版本号
    """
    id: str
    name: str
    description: str = ""
    tasks: List[TaskNode] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tasks': [task.to_dict() for task in self.tasks],
            'metadata': self.metadata,
            'version': self.version
        }


@dataclass
class WorkflowInstance:
    """工作流实例
    
    Attributes:
        workflow_id: 工作流ID
        instance_id: 实例ID
        state: 当前状态
        context: 执行上下文
        results: 任务结果
        start_time: 开始时间
        end_time: 结束时间
        error_message: 错误信息
    """
    workflow_id: str
    instance_id: str
    state: str = "pending"
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'workflow_id': self.workflow_id,
            'instance_id': self.instance_id,
            'state': self.state,
            'context': self.context,
            'results': self.results,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error_message': self.error_message
        }


class WorkflowEngine:
    """工作流引擎
    
    管理和执行工作流
    
    使用示例：
        scheduler = TaskScheduler(max_workers=4)
        engine = WorkflowEngine(scheduler)
        
        # 注册工作流
        workflow = Workflow(
            id="data_pipeline",
            name="Data Pipeline",
            tasks=[
                TaskNode("extract", "Extract Data"),
                TaskNode("transform", "Transform Data", dependencies={"extract"}),
                TaskNode("load", "Load Data", dependencies={"transform"})
            ]
        )
        engine.register_workflow(workflow)
        
        # 创建实例并执行
        instance = engine.create_instance("data_pipeline", context={'source': 'db'})
        results = engine.execute(instance.instance_id)
    """
    
    def __init__(self, scheduler: TaskScheduler):
        self._scheduler = scheduler
        self._workflows: Dict[str, Workflow] = {}
        self._instances: Dict[str, WorkflowInstance] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register_workflow(self, workflow: Workflow) -> None:
        """注册工作流"""
        self._workflows[workflow.id] = workflow
    
    def unregister_workflow(self, workflow_id: str) -> bool:
        """注销工作流"""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流定义"""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """列出所有工作流"""
        return list(self._workflows.values())
    
    def create_instance(self, workflow_id: str, 
                        context: Dict[str, Any] = None) -> WorkflowInstance:
        """创建工作流实例
        
        Args:
            workflow_id: 工作流ID
            context: 执行上下文
            
        Returns:
            工作流实例
            
        Raises:
            ValueError: 工作流不存在
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            instance_id=str(uuid.uuid4())[:8],
            context=context or {}
        )
        
        self._instances[instance.instance_id] = instance
        return instance
    
    def execute(self, instance_id: str, 
                fail_fast: bool = True) -> Dict[str, Any]:
        """执行工作流实例
        
        Args:
            instance_id: 实例ID
            fail_fast: 遇到失败是否立即停止
            
        Returns:
            任务结果字典
            
        Raises:
            ValueError: 实例不存在
        """
        instance = self._instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")
        
        workflow = self._workflows.get(instance.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {instance.workflow_id}")
        
        instance.state = "running"
        instance.start_time = datetime.now()
        
        # 创建新的调度器实例
        from .scheduler import TaskScheduler
        scheduler = TaskScheduler()
        
        # 复制任务处理器
        for task_type, handler in self._scheduler._task_handlers.items():
            scheduler.register_task_handler(task_type, handler)
        
        # 添加任务到调度器
        for task in workflow.tasks:
            scheduler.add_task(task)
        
        try:
            # 执行
            task_results = scheduler.execute(fail_fast=fail_fast)
            
            # 更新实例状态
            instance.results = {
                r.task_id: r.result if r.success else None 
                for r in task_results.values()
            }
            
            all_success = all(r.success for r in task_results.values())
            instance.state = "completed" if all_success else "failed"
            
            if not all_success:
                failed_tasks = [r for r in task_results.values() if not r.success]
                instance.error_message = f"Tasks failed: {[r.task_id for r in failed_tasks]}"
            
        except Exception as e:
            instance.state = "failed"
            instance.error_message = str(e)
        
        instance.end_time = datetime.now()
        
        return instance.results
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取实例信息"""
        return self._instances.get(instance_id)
    
    def get_instance_history(self, workflow_id: str = None) -> List[WorkflowInstance]:
        """获取实例历史"""
        instances = list(self._instances.values())
        
        if workflow_id:
            instances = [i for i in instances if i.workflow_id == workflow_id]
        
        # 按开始时间倒序
        instances.sort(key=lambda i: i.start_time or datetime.min, reverse=True)
        
        return instances
    
    def cancel_instance(self, instance_id: str) -> bool:
        """取消实例执行"""
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        if instance.state == "running":
            instance.state = "cancelled"
            instance.end_time = datetime.now()
            return True
        
        return False
    
    def register_task_handler(self, task_type: str, 
                              handler: Callable[[TaskNode], Any]) -> None:
        """注册任务处理器"""
        self._scheduler.register_task_handler(task_type, handler)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        instances = list(self._instances.values())
        
        return {
            'workflows_count': len(self._workflows),
            'instances_count': len(instances),
            'instances_by_state': {
                'pending': sum(1 for i in instances if i.state == 'pending'),
                'running': sum(1 for i in instances if i.state == 'running'),
                'completed': sum(1 for i in instances if i.state == 'completed'),
                'failed': sum(1 for i in instances if i.state == 'failed'),
                'cancelled': sum(1 for i in instances if i.state == 'cancelled')
            }
        }
