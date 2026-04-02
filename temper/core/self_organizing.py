#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自组织模块 (Self-Organizing Module)

提供工作流定义、任务编排、依赖解析和动态合成功能。
支持串行和并行任务执行，自动解析任务依赖关系。

编码规范：Codong风格错误处理
- 错误返回: {"ok": False, "error": "ERROR_CODE", "message": "详细错误信息"}
- 成功返回: {"ok": True, "value": 返回值}
"""

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import deque


# ============================================================================
# 错误处理工具函数
# ============================================================================

def is_error(result: Dict[str, Any]) -> bool:
    """检查结果是否为错误"""
    return isinstance(result, dict) and result.get("ok") is False


def unwrap(result: Dict[str, Any]) -> Any:
    """从结果中提取值，如果是错误则抛出异常"""
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def ok(value: Any) -> Dict[str, Any]:
    """创建成功结果"""
    return {"ok": True, "value": value}


def err(error_code: str, message: str) -> Dict[str, Any]:
    """创建错误结果"""
    return {"ok": False, "error": error_code, "message": message}


# ============================================================================
# 枚举定义
# ============================================================================

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = auto()      # 等待中
    RUNNING = auto()      # 运行中
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消
    SKIPPED = auto()      # 已跳过


class TaskType(Enum):
    """任务类型枚举"""
    SERIAL = auto()       # 串行任务
    PARALLEL = auto()     # 并行任务
    CONDITIONAL = auto()  # 条件任务
    LOOP = auto()         # 循环任务


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    CREATED = auto()      # 已创建
    RUNNING = auto()      # 运行中
    PAUSED = auto()       # 已暂停
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class Task:
    """任务定义类"""
    id: str
    name: str
    func: Callable[..., Any]
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    task_type: TaskType = TaskType.SERIAL
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    retry_count: int = 0
    retry_delay: float = 0.0
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class TaskResult:
    """任务结果类"""
    task_id: str
    status: TaskStatus
    output: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_attempts: int = 0


@dataclass
class WorkflowDefinition:
    """工作流定义类"""
    id: str
    name: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


# ============================================================================
# DependencyResolver 类 - 依赖解析器
# ============================================================================

class DependencyResolver:
    """
    依赖解析器
    
    负责解析任务之间的依赖关系，构建执行顺序。
    使用拓扑排序算法确保任务按正确顺序执行。
    """
    
    def __init__(self):
        self._graph: Dict[str, Set[str]] = {}  # 任务依赖图
        self._in_degree: Dict[str, int] = {}   # 入度计数
    
    def build_dependency_graph(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """
        构建任务依赖图
        
        Args:
            tasks: 任务字典 {task_id: Task}
            
        Returns:
            Codong风格结果: {"ok": True, "value": graph} 或错误
        """
        try:
            self._graph = {task_id: set() for task_id in tasks}
            self._in_degree = {task_id: 0 for task_id in tasks}
            
            for task_id, task in tasks.items():
                for dep_id in task.dependencies:
                    if dep_id not in tasks:
                        return err(
                            "DEPENDENCY_NOT_FOUND",
                            f"任务 '{task_id}' 依赖的任务 '{dep_id}' 不存在"
                        )
                    
                    # 添加依赖边
                    if task_id not in self._graph[dep_id]:
                        self._graph[dep_id].add(task_id)
                        self._in_degree[task_id] += 1
            
            # 检测循环依赖
            cycle_result = self._detect_cycle(tasks)
            if is_error(cycle_result):
                return cycle_result
            
            return ok({
                "graph": self._graph,
                "in_degree": dict(self._in_degree)
            })
        
        except Exception as e:
            return err("GRAPH_BUILD_ERROR", f"构建依赖图失败: {str(e)}")
    
    def _detect_cycle(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """检测循环依赖"""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return err("CIRCULAR_DEPENDENCY", f"检测到循环依赖涉及任务 '{task_id}'")
        
        return ok(True)
    
    def topological_sort(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """
        拓扑排序获取任务执行顺序
        
        Args:
            tasks: 任务字典
            
        Returns:
            Codong风格结果: {"ok": True, "value": [task_id, ...]} 或错误
        """
        try:
            # 构建依赖图
            graph_result = self.build_dependency_graph(tasks)
            if is_error(graph_result):
                return graph_result
            
            graph_data = unwrap(graph_result)
            in_degree = graph_data["in_degree"].copy()
            
            # Kahn算法进行拓扑排序
            queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
            sorted_order = []
            
            while queue:
                current = queue.popleft()
                sorted_order.append(current)
                
                for neighbor in self._graph.get(current, set()):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            if len(sorted_order) != len(tasks):
                return err("SORT_ERROR", "拓扑排序失败，可能存在循环依赖")
            
            return ok(sorted_order)
        
        except Exception as e:
            return err("TOPOLOGICAL_SORT_ERROR", f"拓扑排序失败: {str(e)}")
    
    def get_ready_tasks(self, tasks: Dict[str, Task], completed: Set[str]) -> Dict[str, Any]:
        """
        获取当前可执行的任务（所有依赖已完成）
        
        Args:
            tasks: 所有任务
            completed: 已完成的任务ID集合
            
        Returns:
            Codong风格结果: {"ok": True, "value": [task_id, ...]}
        """
        try:
            ready = []
            for task_id, task in tasks.items():
                if task_id in completed:
                    continue
                if all(dep_id in completed for dep_id in task.dependencies):
                    ready.append(task_id)
            return ok(ready)
        
        except Exception as e:
            return err("READY_TASKS_ERROR", f"获取就绪任务失败: {str(e)}")
    
    def get_execution_levels(self, tasks: Dict[str, Task]) -> Dict[str, Any]:
        """
        获取任务执行层级（用于并行执行）
        
        返回按层级分组的任务ID，同一层级的任务可以并行执行
        
        Args:
            tasks: 任务字典
            
        Returns:
            Codong风格结果: {"ok": True, "value": [[task_id, ...], ...]}
        """
        try:
            sort_result = self.topological_sort(tasks)
            if is_error(sort_result):
                return sort_result
            
            sorted_order = unwrap(sort_result)
            
            # 计算每个任务的层级
            levels: Dict[str, int] = {}
            for task_id in sorted_order:
                task = tasks[task_id]
                if not task.dependencies:
                    levels[task_id] = 0
                else:
                    max_dep_level = max(levels.get(dep_id, 0) for dep_id in task.dependencies)
                    levels[task_id] = max_dep_level + 1
            
            # 按层级分组
            max_level = max(levels.values()) if levels else 0
            level_groups = [[] for _ in range(max_level + 1)]
            for task_id, level in levels.items():
                level_groups[level].append(task_id)
            
            return ok(level_groups)
        
        except Exception as e:
            return err("EXECUTION_LEVELS_ERROR", f"获取执行层级失败: {str(e)}")


# ============================================================================
# TaskExecutor 类 - 任务执行器
# ============================================================================

class TaskExecutor:
    """
    任务执行器
    
    负责任务的实际执行，支持重试、超时、条件判断等功能。
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._execution_count = 0
        self._lock = threading.Lock()
    
    def execute_task(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务
        
        Args:
            task: 要执行的任务
            context: 执行上下文，包含之前任务的输出
            
        Returns:
            Codong风格结果: {"ok": True, "value": TaskResult} 或错误
        """
        try:
            # 检查条件
            if task.condition and not task.condition(context):
                result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SKIPPED,
                    output=None,
                    start_time=time.time(),
                    end_time=time.time()
                )
                return ok(result)
            
            start_time = time.time()
            retry_attempts = 0
            last_error = None
            
            # 重试循环
            while retry_attempts <= task.retry_count:
                try:
                    # 执行任务函数
                    output = task.func(*task.args, **task.kwargs, **{"context": context})
                    
                    end_time = time.time()
                    result = TaskResult(
                        task_id=task.id,
                        status=TaskStatus.COMPLETED,
                        output=output,
                        start_time=start_time,
                        end_time=end_time,
                        retry_attempts=retry_attempts
                    )
                    
                    with self._lock:
                        self._execution_count += 1
                    
                    return ok(result)
                
                except Exception as e:
                    last_error = str(e)
                    retry_attempts += 1
                    if retry_attempts <= task.retry_count:
                        time.sleep(task.retry_delay)
            
            # 所有重试失败
            end_time = time.time()
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=last_error,
                start_time=start_time,
                end_time=end_time,
                retry_attempts=retry_attempts - 1
            )
            return ok(result)
        
        except Exception as e:
            return err("TASK_EXECUTION_ERROR", f"任务执行失败: {str(e)}")
    
    def execute_parallel(self, tasks: List[Task], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        并行执行多个任务
        
        Args:
            tasks: 要执行的任务列表
            context: 执行上下文
            
        Returns:
            Codong风格结果: {"ok": True, "value": {task_id: TaskResult, ...}}
        """
        try:
            results = {}
            futures = {}
            
            for task in tasks:
                future = self._thread_pool.submit(self._execute_task_wrapper, task, context)
                futures[future] = task
            
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    if is_error(result):
                        error_msg = result.get("message", "未知错误")
                        results[task.id] = TaskResult(
                            task_id=task.id,
                            status=TaskStatus.FAILED,
                            error=error_msg
                        )
                    else:
                        results[task.id] = unwrap(result)
                except Exception as e:
                    results[task.id] = TaskResult(
                        task_id=task.id,
                        status=TaskStatus.FAILED,
                        error=str(e)
                    )
            
            return ok(results)
        
        except Exception as e:
            return err("PARALLEL_EXECUTION_ERROR", f"并行执行失败: {str(e)}")
    
    def _execute_task_wrapper(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """任务执行包装器（用于线程池）"""
        return self.execute_task(task, context)
    
    def get_execution_count(self) -> int:
        """获取执行计数"""
        with self._lock:
            return self._execution_count
    
    def shutdown(self):
        """关闭执行器"""
        self._thread_pool.shutdown(wait=True)


# ============================================================================
# Workflow 类 - 工作流定义
# ============================================================================

class Workflow:
    """
    工作流类
    
    提供声明式工作流定义，支持链式调用构建工作流。
    """
    
    def __init__(self, name: str = "", workflow_id: str = ""):
        self.id = workflow_id or str(uuid.uuid4())
        self.name = name or f"Workflow_{self.id[:8]}"
        self._tasks: Dict[str, Task] = {}
        self._metadata: Dict[str, Any] = {}
        self._last_task_id: Optional[str] = None
    
    def add_task(
        self,
        func: Callable[..., Any],
        name: str = "",
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        task_type: TaskType = TaskType.SERIAL,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        retry_count: int = 0,
        retry_delay: float = 0.0,
        timeout: Optional[float] = None,
        task_id: str = ""
    ) -> Dict[str, Any]:
        """
        添加任务到工作流
        
        Args:
            func: 任务函数
            name: 任务名称
            args: 位置参数
            kwargs: 关键字参数
            dependencies: 依赖的任务ID列表
            task_type: 任务类型
            condition: 执行条件函数
            retry_count: 重试次数
            retry_delay: 重试延迟（秒）
            timeout: 超时时间（秒）
            task_id: 任务ID（可选）
            
        Returns:
            Codong风格结果: {"ok": True, "value": task_id}
        """
        try:
            task_id = task_id or str(uuid.uuid4())
            task_name = name or func.__name__
            
            # 如果没有指定依赖，默认依赖上一个任务
            deps = dependencies or []
            if not deps and self._last_task_id and task_type == TaskType.SERIAL:
                deps = [self._last_task_id]
            
            task = Task(
                id=task_id,
                name=task_name,
                func=func,
                args=args,
                kwargs=kwargs or {},
                dependencies=deps,
                task_type=task_type,
                condition=condition,
                retry_count=retry_count,
                retry_delay=retry_delay,
                timeout=timeout
            )
            
            self._tasks[task_id] = task
            self._last_task_id = task_id
            
            return ok(task_id)
        
        except Exception as e:
            return err("ADD_TASK_ERROR", f"添加任务失败: {str(e)}")
    
    def then(
        self,
        func: Callable[..., Any],
        name: str = "",
        args: Tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        **options
    ) -> "Workflow":
        """
        链式添加串行任务
        
        Args:
            func: 任务函数
            name: 任务名称
            args: 位置参数
            kwargs: 关键字参数
            **options: 其他选项
            
        Returns:
            self（支持链式调用）
        """
        result = self.add_task(
            func=func,
            name=name,
            args=args,
            kwargs=kwargs,
            task_type=TaskType.SERIAL,
            **options
        )
        if is_error(result):
            raise RuntimeError(unwrap(err("CHAIN_ERROR", "链式调用失败")))
        return self
    
    def parallel(
        self,
        funcs: List[Callable[..., Any]],
        names: Optional[List[str]] = None,
        common_dependencies: Optional[List[str]] = None
    ) -> "Workflow":
        """
        添加并行任务组
        
        Args:
            funcs: 任务函数列表
            names: 任务名称列表
            common_dependencies: 共同依赖的任务ID
            
        Returns:
            self（支持链式调用）
        """
        try:
            parallel_task_ids = []
            
            for i, func in enumerate(funcs):
                name = names[i] if names and i < len(names) else f"{func.__name__}_{i}"
                result = self.add_task(
                    func=func,
                    name=name,
                    dependencies=common_dependencies or [],
                    task_type=TaskType.PARALLEL
                )
                if is_error(result):
                    raise RuntimeError("添加并行任务失败")
                parallel_task_ids.append(unwrap(result))
            
            # 更新最后一个任务ID为并行任务组的最后一个
            if parallel_task_ids:
                self._last_task_id = parallel_task_ids[-1]
            
            return self
        
        except Exception as e:
            raise RuntimeError(f"并行任务添加失败: {str(e)}")
    
    def when(
        self,
        condition: Callable[[Dict[str, Any]], bool],
        func: Callable[..., Any],
        name: str = "",
        **options
    ) -> "Workflow":
        """
        添加条件任务
        
        Args:
            condition: 条件函数
            func: 任务函数
            name: 任务名称
            **options: 其他选项
            
        Returns:
            self（支持链式调用）
        """
        result = self.add_task(
            func=func,
            name=name,
            condition=condition,
            task_type=TaskType.CONDITIONAL,
            **options
        )
        if is_error(result):
            raise RuntimeError("条件任务添加失败")
        return self
    
    def remove_task(self, task_id: str) -> Dict[str, Any]:
        """
        移除任务
        
        Args:
            task_id: 要移除的任务ID
            
        Returns:
            Codong风格结果
        """
        try:
            if task_id not in self._tasks:
                return err("TASK_NOT_FOUND", f"任务 '{task_id}' 不存在")
            
            # 检查是否有其他任务依赖此任务
            for tid, task in self._tasks.items():
                if task_id in task.dependencies:
                    return err("TASK_HAS_DEPENDENTS", f"任务 '{task_id}' 被其他任务依赖，无法移除")
            
            del self._tasks[task_id]
            
            if self._last_task_id == task_id:
                self._last_task_id = None
            
            return ok(True)
        
        except Exception as e:
            return err("REMOVE_TASK_ERROR", f"移除任务失败: {str(e)}")
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Codong风格结果: {"ok": True, "value": Task}
        """
        try:
            if task_id not in self._tasks:
                return err("TASK_NOT_FOUND", f"任务 '{task_id}' 不存在")
            return ok(self._tasks[task_id])
        
        except Exception as e:
            return err("GET_TASK_ERROR", f"获取任务失败: {str(e)}")
    
    def get_tasks(self) -> Dict[str, Task]:
        """获取所有任务"""
        return dict(self._tasks)
    
    def set_metadata(self, key: str, value: Any) -> Dict[str, Any]:
        """设置元数据"""
        try:
            self._metadata[key] = value
            return ok(True)
        except Exception as e:
            return err("SET_METADATA_ERROR", f"设置元数据失败: {str(e)}")
    
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """获取元数据"""
        try:
            return ok(self._metadata.get(key))
        except Exception as e:
            return err("GET_METADATA_ERROR", f"获取元数据失败: {str(e)}")
    
    def to_definition(self) -> Dict[str, Any]:
        """
        转换为工作流定义
        
        Returns:
            Codong风格结果: {"ok": True, "value": WorkflowDefinition}
        """
        try:
            definition = WorkflowDefinition(
                id=self.id,
                name=self.name,
                tasks=dict(self._tasks),
                metadata=dict(self._metadata)
            )
            return ok(definition)
        
        except Exception as e:
            return err("TO_DEFINITION_ERROR", f"转换定义失败: {str(e)}")
    
    def validate(self) -> Dict[str, Any]:
        """
        验证工作流
        
        Returns:
            Codong风格结果
        """
        try:
            if not self._tasks:
                return err("EMPTY_WORKFLOW", "工作流没有任务")
            
            resolver = DependencyResolver()
            result = resolver.topological_sort(self._tasks)
            if is_error(result):
                return result
            
            return ok({"valid": True, "task_count": len(self._tasks)})
        
        except Exception as e:
            return err("VALIDATION_ERROR", f"验证失败: {str(e)}")
    
    def clear(self) -> Dict[str, Any]:
        """清空工作流"""
        try:
            self._tasks.clear()
            self._metadata.clear()
            self._last_task_id = None
            return ok(True)
        except Exception as e:
            return err("CLEAR_ERROR", f"清空失败: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "name": self.name,
            "tasks": {
                tid: {
                    "id": t.id,
                    "name": t.name,
                    "dependencies": t.dependencies,
                    "task_type": t.task_type.name,
                    "retry_count": t.retry_count,
                    "timeout": t.timeout
                }
                for tid, t in self._tasks.items()
            },
            "metadata": self._metadata
        }
    
    def __repr__(self) -> str:
        return f"Workflow(id={self.id}, name={self.name}, tasks={len(self._tasks)})"


# ============================================================================
# WorkflowEngine 类 - 工作流引擎
# ============================================================================

class WorkflowEngine:
    """
    工作流引擎
    
    负责工作流的执行管理，支持串行、并行、条件执行等模式。
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._executor = TaskExecutor(max_workers=max_workers)
        self._workflows: Dict[str, Workflow] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def register_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """
        注册工作流
        
        Args:
            workflow: 工作流实例
            
        Returns:
            Codong风格结果
        """
        try:
            # 验证工作流
            validation = workflow.validate()
            if is_error(validation):
                return validation
            
            self._workflows[workflow.id] = workflow
            return ok({"workflow_id": workflow.id, "registered": True})
        
        except Exception as e:
            return err("REGISTER_ERROR", f"注册工作流失败: {str(e)}")
    
    def unregister_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        注销工作流
        
        Args:
            workflow_id: 工作流ID
            
        Returns:
            Codong风格结果
        """
        try:
            if workflow_id not in self._workflows:
                return err("WORKFLOW_NOT_FOUND", f"工作流 '{workflow_id}' 不存在")
            
            del self._workflows[workflow_id]
            return ok(True)
        
        except Exception as e:
            return err("UNREGISTER_ERROR", f"注销工作流失败: {str(e)}")
    
    def execute(
        self,
        workflow: Union[Workflow, str],
        initial_context: Optional[Dict[str, Any]] = None,
        mode: str = "auto"
    ) -> Dict[str, Any]:
        """
        执行工作流
        
        Args:
            workflow: 工作流实例或ID
            initial_context: 初始上下文
            mode: 执行模式 ("auto", "serial", "parallel")
            
        Returns:
            Codong风格结果: {"ok": True, "value": execution_result}
        """
        try:
            # 获取工作流
            if isinstance(workflow, str):
                if workflow not in self._workflows:
                    return err("WORKFLOW_NOT_FOUND", f"工作流 '{workflow}' 不存在")
                wf = self._workflows[workflow]
            else:
                wf = workflow
            
            # 验证工作流
            validation = wf.validate()
            if is_error(validation):
                return validation
            
            # 初始化执行上下文
            context = dict(initial_context or {})
            context["_workflow_id"] = wf.id
            context["_workflow_name"] = wf.name
            context["_start_time"] = time.time()
            
            tasks = wf.get_tasks()
            
            # 根据模式选择执行策略
            if mode == "serial":
                result = self._execute_serial(tasks, context)
            elif mode == "parallel":
                result = self._execute_parallel(tasks, context)
            else:  # auto mode
                result = self._execute_auto(tasks, context)
            
            if is_error(result):
                return result
            
            execution_result = unwrap(result)
            
            # 记录执行历史
            with self._lock:
                self._execution_history.append({
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "timestamp": time.time(),
                    "result": execution_result
                })
            
            return ok(execution_result)
        
        except Exception as e:
            return err("EXECUTION_ERROR", f"工作流执行失败: {str(e)}")
    
    def _execute_serial(
        self,
        tasks: Dict[str, Task],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """串行执行任务"""
        try:
            resolver = DependencyResolver()
            sort_result = resolver.topological_sort(tasks)
            if is_error(sort_result):
                return sort_result
            
            execution_order = unwrap(sort_result)
            results = {}
            task_outputs = {}
            
            for task_id in execution_order:
                task = tasks[task_id]
                
                # 更新上下文
                context["_previous_outputs"] = task_outputs
                
                # 执行任务
                exec_result = self._executor.execute_task(task, context)
                if is_error(exec_result):
                    return exec_result
                
                task_result = unwrap(exec_result)
                results[task_id] = task_result
                
                if task_result.status == TaskStatus.COMPLETED:
                    task_outputs[task_id] = task_result.output
                elif task_result.status == TaskStatus.FAILED:
                    return ok({
                        "status": WorkflowStatus.FAILED.name,
                        "failed_task": task_id,
                        "error": task_result.error,
                        "results": results
                    })
            
            return ok({
                "status": WorkflowStatus.COMPLETED.name,
                "results": results,
                "outputs": task_outputs,
                "execution_time": time.time() - context["_start_time"]
            })
        
        except Exception as e:
            return err("SERIAL_EXECUTION_ERROR", f"串行执行失败: {str(e)}")
    
    def _execute_parallel(
        self,
        tasks: Dict[str, Task],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """并行执行任务（按层级）"""
        try:
            resolver = DependencyResolver()
            levels_result = resolver.get_execution_levels(tasks)
            if is_error(levels_result):
                return levels_result
            
            execution_levels = unwrap(levels_result)
            results = {}
            task_outputs = {}
            
            for level_idx, level_tasks in enumerate(execution_levels):
                level_task_objects = [tasks[tid] for tid in level_tasks if tid in tasks]
                
                if not level_task_objects:
                    continue
                
                # 更新上下文
                context["_previous_outputs"] = task_outputs
                context["_current_level"] = level_idx
                
                # 并行执行当前层级的任务
                exec_result = self._executor.execute_parallel(level_task_objects, context)
                if is_error(exec_result):
                    return exec_result
                
                level_results = unwrap(exec_result)
                
                # 处理结果
                for task_id, task_result in level_results.items():
                    results[task_id] = task_result
                    
                    if task_result.status == TaskStatus.COMPLETED:
                        task_outputs[task_id] = task_result.output
                    elif task_result.status == TaskStatus.FAILED:
                        return ok({
                            "status": WorkflowStatus.FAILED.name,
                            "failed_task": task_id,
                            "error": task_result.error,
                            "results": results
                        })
            
            return ok({
                "status": WorkflowStatus.COMPLETED.name,
                "results": results,
                "outputs": task_outputs,
                "execution_time": time.time() - context["_start_time"]
            })
        
        except Exception as e:
            return err("PARALLEL_EXECUTION_ERROR", f"并行执行失败: {str(e)}")
    
    def _execute_auto(
        self,
        tasks: Dict[str, Task],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """自动模式执行（动态调度）"""
        try:
            resolver = DependencyResolver()
            completed: Set[str] = set()
            results = {}
            task_outputs = {}
            failed = False
            
            while len(completed) < len(tasks) and not failed:
                # 获取当前可执行的任务
                ready_result = resolver.get_ready_tasks(tasks, completed)
                if is_error(ready_result):
                    return ready_result
                
                ready_tasks = unwrap(ready_result)
                
                if not ready_tasks:
                    if len(completed) < len(tasks):
                        return err("DEADLOCK", "检测到死锁，无法继续执行")
                    break
                
                # 准备执行任务
                ready_task_objects = [tasks[tid] for tid in ready_tasks]
                context["_previous_outputs"] = task_outputs
                
                # 并行执行就绪任务
                exec_result = self._executor.execute_parallel(ready_task_objects, context)
                if is_error(exec_result):
                    return exec_result
                
                level_results = unwrap(exec_result)
                
                # 处理结果
                for task_id, task_result in level_results.items():
                    results[task_id] = task_result
                    completed.add(task_id)
                    
                    if task_result.status == TaskStatus.COMPLETED:
                        task_outputs[task_id] = task_result.output
                    elif task_result.status == TaskStatus.FAILED:
                        failed = True
                        return ok({
                            "status": WorkflowStatus.FAILED.name,
                            "failed_task": task_id,
                            "error": task_result.error,
                            "results": results
                        })
            
            return ok({
                "status": WorkflowStatus.COMPLETED.name,
                "results": results,
                "outputs": task_outputs,
                "execution_time": time.time() - context["_start_time"]
            })
        
        except Exception as e:
            return err("AUTO_EXECUTION_ERROR", f"自动执行失败: {str(e)}")
    
    def synthesize(
        self,
        base_workflow: Workflow,
        conditions: Dict[str, Callable[[Dict[str, Any]], bool]],
        extensions: Dict[str, Workflow]
    ) -> Dict[str, Any]:
        """
        动态合成工作流
        
        根据条件动态选择和组合子工作流
        
        Args:
            base_workflow: 基础工作流
            conditions: 条件字典 {condition_name: condition_func}
            extensions: 扩展工作流字典 {condition_name: Workflow}
            
        Returns:
            Codong风格结果: {"ok": True, "value": synthesized_workflow}
        """
        try:
            # 创建新工作流
            new_workflow = Workflow(
                name=f"{base_workflow.name}_synthesized",
                workflow_id=str(uuid.uuid4())
            )
            
            # 复制基础任务
            for task_id, task in base_workflow.get_tasks().items():
                new_workflow._tasks[task_id] = Task(
                    id=task.id,
                    name=task.name,
                    func=task.func,
                    args=task.args,
                    kwargs=task.kwargs,
                    dependencies=task.dependencies.copy(),
                    task_type=task.task_type,
                    condition=task.condition,
                    retry_count=task.retry_count,
                    retry_delay=task.retry_delay,
                    timeout=task.timeout,
                    metadata=task.metadata.copy()
                )
            
            # 根据条件添加扩展
            dummy_context = {}
            for condition_name, condition_func in conditions.items():
                if condition_func(dummy_context) and condition_name in extensions:
                    ext_workflow = extensions[condition_name]
                    
                    # 添加扩展工作流的任务
                    for task_id, task in ext_workflow.get_tasks().items():
                        new_task_id = f"{condition_name}_{task_id}"
                        new_workflow._tasks[new_task_id] = Task(
                            id=new_task_id,
                            name=f"{condition_name}.{task.name}",
                            func=task.func,
                            args=task.args,
                            kwargs=task.kwargs,
                            dependencies=[f"{condition_name}_{dep}" for dep in task.dependencies],
                            task_type=task.task_type,
                            condition=task.condition,
                            retry_count=task.retry_count,
                            retry_delay=task.retry_delay,
                            timeout=task.timeout
                        )
            
            return ok(new_workflow)
        
        except Exception as e:
            return err("SYNTHESIS_ERROR", f"工作流合成失败: {str(e)}")
    
    def get_execution_history(self) -> Dict[str, Any]:
        """获取执行历史"""
        try:
            with self._lock:
                return ok(list(self._execution_history))
        except Exception as e:
            return err("GET_HISTORY_ERROR", f"获取历史失败: {str(e)}")
    
    def clear_history(self) -> Dict[str, Any]:
        """清空执行历史"""
        try:
            with self._lock:
                self._execution_history.clear()
            return ok(True)
        except Exception as e:
            return err("CLEAR_HISTORY_ERROR", f"清空历史失败: {str(e)}")
    
    def shutdown(self):
        """关闭引擎"""
        self._executor.shutdown()


# ============================================================================
# 全局工作流函数
# ============================================================================

# 全局引擎实例
_global_engine: Optional[WorkflowEngine] = None
_global_engine_lock = threading.Lock()


def get_global_engine(max_workers: int = 4) -> WorkflowEngine:
    """获取全局工作流引擎实例"""
    global _global_engine
    with _global_engine_lock:
        if _global_engine is None:
            _global_engine = WorkflowEngine(max_workers=max_workers)
        return _global_engine


def create_workflow(name: str = "") -> Workflow:
    """创建新工作流"""
    return Workflow(name=name)


def run_workflow(
    workflow: Workflow,
    context: Optional[Dict[str, Any]] = None,
    mode: str = "auto"
) -> Dict[str, Any]:
    """
    运行工作流（便捷函数）
    
    Args:
        workflow: 工作流实例
        context: 执行上下文
        mode: 执行模式
        
    Returns:
        Codong风格结果
    """
    engine = get_global_engine()
    return engine.execute(workflow, context, mode)


def parallel_tasks(*funcs: Callable[..., Any]) -> Workflow:
    """
    创建并行任务工作流（便捷函数）
    
    Args:
        *funcs: 任务函数列表
        
    Returns:
        Workflow实例
    """
    workflow = Workflow(name="parallel_workflow")
    workflow.parallel(list(funcs))
    return workflow


def serial_tasks(*funcs: Callable[..., Any]) -> Workflow:
    """
    创建串行任务工作流（便捷函数）
    
    Args:
        *funcs: 任务函数列表
        
    Returns:
        Workflow实例
    """
    workflow = Workflow(name="serial_workflow")
    for func in funcs:
        workflow.then(func)
    return workflow


def conditional_workflow(
    condition: Callable[[Dict[str, Any]], bool],
    true_branch: Callable[..., Any],
    false_branch: Optional[Callable[..., Any]] = None
) -> Workflow:
    """
    创建条件工作流（便捷函数）
    
    Args:
        condition: 条件函数
        true_branch: 条件为真时执行的任务
        false_branch: 条件为假时执行的任务（可选）
        
    Returns:
        Workflow实例
    """
    workflow = Workflow(name="conditional_workflow")
    workflow.when(condition, true_branch, name="true_branch")
    if false_branch:
        workflow.when(lambda ctx: not condition(ctx), false_branch, name="false_branch")
    return workflow


def compose_workflows(*workflows: Workflow) -> Workflow:
    """
    组合多个工作流
    
    Args:
        *workflows: 工作流实例列表
        
    Returns:
        组合后的Workflow实例
    """
    composed = Workflow(name="composed_workflow")
    last_task_id = None
    
    for i, wf in enumerate(workflows):
        tasks = wf.get_tasks()
        
        # 调整任务ID避免冲突
        id_mapping = {}
        for old_id, task in tasks.items():
            new_id = f"wf{i}_{old_id}"
            id_mapping[old_id] = new_id
            
            # 调整依赖
            new_deps = []
            for dep in task.dependencies:
                if dep in id_mapping:
                    new_deps.append(id_mapping[dep])
                else:
                    # 依赖前一个工作流的最后一个任务
                    if last_task_id:
                        new_deps.append(last_task_id)
            
            composed._tasks[new_id] = Task(
                id=new_id,
                name=f"{wf.name}.{task.name}",
                func=task.func,
                args=task.args,
                kwargs=task.kwargs,
                dependencies=new_deps,
                task_type=task.task_type,
                condition=task.condition,
                retry_count=task.retry_count,
                retry_delay=task.retry_delay,
                timeout=task.timeout
            )
            
            last_task_id = new_id
    
    composed._last_task_id = last_task_id
    return composed


def shutdown_global_engine():
    """关闭全局引擎"""
    global _global_engine
    with _global_engine_lock:
        if _global_engine:
            _global_engine.shutdown()
            _global_engine = None


# ============================================================================
# 示例和测试
# ============================================================================

if __name__ == "__main__":
    # 示例任务函数
    def task_a(context=None):
        print("执行任务 A")
        return "result_a"
    
    def task_b(context=None):
        print("执行任务 B")
        return "result_b"
    
    def task_c(context=None):
        print("执行任务 C")
        prev = context.get("_previous_outputs", {})
        return f"result_c based on {prev}"
    
    def task_d(context=None):
        print("执行任务 D")
        return "result_d"
    
    # 测试1: 串行工作流
    print("=" * 50)
    print("测试1: 串行工作流")
    print("=" * 50)
    
    workflow1 = create_workflow("serial_test")
    workflow1.then(task_a, name="step1")
    workflow1.then(task_b, name="step2")
    workflow1.then(task_c, name="step3")
    
    result1 = run_workflow(workflow1, mode="serial")
    print(f"结果: {result1}")
    
    # 测试2: 并行工作流
    print("\n" + "=" * 50)
    print("测试2: 并行工作流")
    print("=" * 50)
    
    workflow2 = create_workflow("parallel_test")
    workflow2.parallel([task_a, task_b, task_d], common_dependencies=[])
    workflow2.then(task_c, name="final")
    
    result2 = run_workflow(workflow2, mode="parallel")
    print(f"结果: {result2}")
    
    # 测试3: 条件工作流
    print("\n" + "=" * 50)
    print("测试3: 条件工作流")
    print("=" * 50)
    
    def should_run(ctx):
        return ctx.get("run_special", False)
    
    workflow3 = create_workflow("conditional_test")
    workflow3.then(task_a, name="always_run")
    workflow3.when(should_run, task_b, name="conditional_task")
    workflow3.then(task_c, name="final_task")
    
    result3a = run_workflow(workflow3, context={"run_special": True})
    print(f"条件为真结果: {result3a}")
    
    result3b = run_workflow(workflow3, context={"run_special": False})
    print(f"条件为假结果: {result3b}")
    
    # 测试4: 依赖解析
    print("\n" + "=" * 50)
    print("测试4: 依赖解析")
    print("=" * 50)
    
    resolver = DependencyResolver()
    tasks = workflow2.get_tasks()
    
    levels_result = resolver.get_execution_levels(tasks)
    if not is_error(levels_result):
        levels = unwrap(levels_result)
        print(f"执行层级: {levels}")
    
    # 测试5: 工作流合成
    print("\n" + "=" * 50)
    print("测试5: 工作流合成")
    print("=" * 50)
    
    base_wf = create_workflow("base")
    base_wf.then(task_a, name="base_task")
    
    ext_wf = create_workflow("extension")
    ext_wf.then(task_b, name="ext_task")
    
    engine = get_global_engine()
    conditions = {"add_extension": lambda ctx: True}
    extensions = {"add_extension": ext_wf}
    
    synth_result = engine.synthesize(base_wf, conditions, extensions)
    print(f"合成结果: {synth_result}")
    
    # 清理
    shutdown_global_engine()
    print("\n所有测试完成！")
