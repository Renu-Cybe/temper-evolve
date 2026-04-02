"""
任务调度器

负责任务的调度和执行
"""

from typing import Callable, Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import datetime
from .graph import DependencyGraph, TaskNode, NodeState
import threading
import time


@dataclass
class TaskResult:
    """任务执行结果
    
    Attributes:
        task_id: 任务ID
        success: 是否成功
        result: 执行结果
        error: 错误信息
        start_time: 开始时间
        end_time: 结束时间
        retry_count: 重试次数
    """
    task_id: str
    success: bool
    result: Any
    error: Optional[str]
    start_time: datetime
    end_time: datetime
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': (self.end_time - self.start_time).total_seconds(),
            'retry_count': self.retry_count
        }


class TaskScheduler:
    """任务调度器
    
    负责任务的并行调度和执行
    
    使用示例：
        scheduler = TaskScheduler(max_workers=4)
        
        # 注册任务处理器
        scheduler.register_task_handler("default", my_task_handler)
        
        # 添加任务
        scheduler.add_task(TaskNode("A", "Task A"))
        scheduler.add_task(TaskNode("B", "Task B", dependencies={"A"}))
        
        # 执行
        results = scheduler.execute()
    """
    
    def __init__(self, max_workers: int = 4):
        self._graph = DependencyGraph()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._task_handlers: Dict[str, Callable] = {}
        self._running_tasks: Dict[str, Future] = {}
        self._results: Dict[str, TaskResult] = {}
        self._lock = threading.RLock()
        self._stop_requested = False
    
    def register_task_handler(self, task_type: str, 
                              handler: Callable[[TaskNode], Any]) -> None:
        """注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，接收 TaskNode，返回结果
        """
        self._task_handlers[task_type] = handler
    
    def add_task(self, node: TaskNode) -> None:
        """添加任务"""
        self._graph.add_node(node)
    
    def execute(self, fail_fast: bool = True) -> Dict[str, TaskResult]:
        """执行所有任务
        
        Args:
            fail_fast: 遇到失败是否立即停止
            
        Returns:
            任务执行结果字典
            
        Raises:
            ValueError: 如果存在循环依赖
        """
        # 检查循环依赖
        cycle = self._graph.detect_cycles()
        if cycle:
            raise ValueError(f"Cannot execute: circular dependency {cycle}")
        
        self._stop_requested = False
        
        while not self._stop_requested:
            # 获取就绪任务
            ready_nodes = self._graph.get_ready_nodes()
            
            if not ready_nodes and not self._running_tasks:
                break  # 所有任务完成
            
            # 启动就绪任务
            for node in ready_nodes:
                self._start_task(node)
            
            # 等待至少一个任务完成
            completed = self._wait_for_any(timeout=1.0)
            
            # 检查失败
            if fail_fast and completed:
                for task_id in completed:
                    result = self._results.get(task_id)
                    if result and not result.success:
                        # 取消所有运行中的任务
                        self._cancel_all()
                        return self._results
        
        return self._results
    
    def _start_task(self, node: TaskNode) -> None:
        """启动任务"""
        node.state = NodeState.RUNNING
        start_time = datetime.now()
        
        task_type = node.metadata.get('type', 'default')
        handler = self._task_handlers.get(task_type)
        
        if not handler:
            node.state = NodeState.FAILED
            node.error = f"No handler for task type: {task_type}"
            self._results[node.id] = TaskResult(
                task_id=node.id,
                success=False,
                result=None,
                error=node.error,
                start_time=start_time,
                end_time=datetime.now()
            )
            return
        
        def run_task():
            retry_count = 0
            max_retries = node.max_retries
            
            while retry_count <= max_retries:
                try:
                    result = handler(node)
                    return TaskResult(
                        task_id=node.id,
                        success=True,
                        result=result,
                        error=None,
                        start_time=start_time,
                        end_time=datetime.now(),
                        retry_count=retry_count
                    )
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        return TaskResult(
                            task_id=node.id,
                            success=False,
                            result=None,
                            error=str(e),
                            start_time=start_time,
                            end_time=datetime.now(),
                            retry_count=retry_count - 1
                        )
                    # 重试前等待
                    time.sleep(1)
        
        future = self._executor.submit(run_task)
        self._running_tasks[node.id] = future
    
    def _wait_for_any(self, timeout: float = None) -> List[str]:
        """等待至少一个任务完成
        
        Returns:
            完成的任务ID列表
        """
        import concurrent.futures
        
        if not self._running_tasks:
            return []
        
        completed_ids = []
        
        # 检查已完成的任务
        for task_id, future in list(self._running_tasks.items()):
            if future.done():
                completed_ids.append(task_id)
                self._handle_completed(task_id, future)
        
        if completed_ids:
            return completed_ids
        
        # 等待新完成的任务
        if self._running_tasks:
            done, _ = concurrent.futures.wait(
                self._running_tasks.values(),
                timeout=timeout,
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            for future in done:
                # 找到对应的任务ID
                for tid, f in list(self._running_tasks.items()):
                    if f == future:
                        completed_ids.append(tid)
                        self._handle_completed(tid, future)
                        break
        
        return completed_ids
    
    def _handle_completed(self, task_id: str, future: Future) -> None:
        """处理完成的任务"""
        try:
            result = future.result()
        except Exception as e:
            result = TaskResult(
                task_id=task_id,
                success=False,
                result=None,
                error=str(e),
                start_time=datetime.now(),
                end_time=datetime.now()
            )
        
        self._results[task_id] = result
        
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]
        
        # 更新节点状态
        node = self._graph.get_node(task_id)
        if node:
            if result.success:
                node.state = NodeState.COMPLETED
                node.result = result.result
            else:
                node.state = NodeState.FAILED
                node.error = result.error
    
    def _cancel_all(self) -> None:
        """取消所有运行中的任务"""
        for task_id, future in self._running_tasks.items():
            future.cancel()
            node = self._graph.get_node(task_id)
            if node:
                node.state = NodeState.CANCELLED
        
        self._running_tasks.clear()
    
    def stop(self) -> None:
        """停止调度器"""
        self._stop_requested = True
        self._cancel_all()
        self._executor.shutdown(wait=False)
    
    def get_progress(self) -> dict:
        """获取执行进度"""
        stats = self._graph.get_stats()
        total = stats['total_nodes']
        completed = stats['states'].get('completed', 0)
        failed = stats['states'].get('failed', 0)
        running = stats['states'].get('running', 0)
        
        done = completed + failed
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': total - done - running,
            'percent': (done / total * 100) if total > 0 else 0
        }
    
    def get_results(self) -> Dict[str, TaskResult]:
        """获取所有结果"""
        return self._results.copy()
