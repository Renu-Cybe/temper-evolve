"""
操作追踪器 - 追踪操作的完整生命周期

提供上下文管理器，自动追踪操作的开始、成功和失败
"""

from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
import uuid

from .logger import AuditLogger, AuditCategory, AuditLevel


class OperationTracer:
    """操作追踪器
    
    使用上下文管理器追踪操作的完整生命周期，自动记录：
    - 操作开始
    - 操作成功完成
    - 操作失败（包含异常信息）
    
    使用示例：
        tracer = OperationTracer(audit_logger)
        
        with tracer.trace(
            category=AuditCategory.USER_ACTION,
            action="file.edit",
            source="editor",
            parameters={'file': 'test.txt'}
        ) as op:
            # 执行操作
            edit_file('test.txt', content)
            # 操作成功会自动记录
        
        # 如果发生异常，会自动记录失败
    """
    
    def __init__(self, audit_logger: AuditLogger):
        self._audit = audit_logger
        self._context_stack: list = []
    
    @contextmanager
    def trace(self, 
              category: AuditCategory,
              action: str,
              source: str,
              parameters: Dict[str, Any] = None,
              user: str = None,
              context: Dict[str, Any] = None) -> Generator[Any, None, None]:
        """追踪操作上下文
        
        Args:
            category: 审计类别
            action: 操作名称
            source: 来源模块
            parameters: 操作参数
            user: 用户标识
            context: 额外上下文
            
        Yields:
            操作记录对象
        """
        correlation_id = str(uuid.uuid4())[:8]
        parent_id = self._context_stack[-1] if self._context_stack else None
        
        # 记录开始
        start_record = self._audit.log(
            level=AuditLevel.INFO,
            category=category,
            action=f"{action}.start",
            source=source,
            parameters=parameters,
            correlation_id=correlation_id,
            parent_id=parent_id,
            user=user,
            context=context
        )
        
        self._context_stack.append(start_record.id)
        
        try:
            yield start_record
            
            # 记录成功
            self._audit.log(
                level=AuditLevel.INFO,
                category=category,
                action=f"{action}.complete",
                source=source,
                result="success",
                correlation_id=correlation_id,
                parent_id=parent_id,
                user=user
            )
            
        except Exception as e:
            # 记录失败
            self._audit.log(
                level=AuditLevel.ERROR,
                category=category,
                action=f"{action}.failed",
                source=source,
                result="failure",
                error_message=str(e),
                correlation_id=correlation_id,
                parent_id=parent_id,
                user=user
            )
            raise
        finally:
            self._context_stack.pop()
    
    def get_current_context(self) -> Optional[str]:
        """获取当前上下文ID（用于嵌套操作）"""
        return self._context_stack[-1] if self._context_stack else None
    
    def get_context_depth(self) -> int:
        """获取当前上下文嵌套深度"""
        return len(self._context_stack)
    
    def create_span(self, 
                    category: AuditCategory,
                    action: str,
                    source: str,
                    **kwargs) -> 'OperationSpan':
        """创建手动控制的追踪跨度"""
        return OperationSpan(self._audit, category, action, source, 
                            self._context_stack, **kwargs)


class OperationSpan:
    """手动控制的追踪跨度
    
    用于需要更精细控制的场景
    """
    
    def __init__(self, 
                 audit: AuditLogger,
                 category: AuditCategory,
                 action: str,
                 source: str,
                 context_stack: list,
                 parameters: Dict[str, Any] = None,
                 user: str = None):
        self._audit = audit
        self._category = category
        self._action = action
        self._source = source
        self._context_stack = context_stack
        self._parameters = parameters or {}
        self._user = user
        self._correlation_id = str(uuid.uuid4())[:8]
        self._parent_id = context_stack[-1] if context_stack else None
        self._record_id = None
        self._completed = False
    
    def start(self) -> 'OperationSpan':
        """开始追踪"""
        record = self._audit.log(
            level=AuditLevel.INFO,
            category=self._category,
            action=f"{self._action}.start",
            source=self._source,
            parameters=self._parameters,
            correlation_id=self._correlation_id,
            parent_id=self._parent_id,
            user=self._user
        )
        self._record_id = record.id
        self._context_stack.append(record.id)
        return self
    
    def success(self, result_data: Dict[str, Any] = None) -> None:
        """标记成功"""
        if self._completed:
            return
        
        self._audit.log(
            level=AuditLevel.INFO,
            category=self._category,
            action=f"{self._action}.complete",
            source=self._source,
            result="success",
            parameters=result_data,
            correlation_id=self._correlation_id,
            parent_id=self._parent_id,
            user=self._user
        )
        self._completed = True
        self._cleanup()
    
    def failure(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """标记失败"""
        if self._completed:
            return
        
        self._audit.log(
            level=AuditLevel.ERROR,
            category=self._category,
            action=f"{self._action}.failed",
            source=self._source,
            result="failure",
            error_message=str(error),
            context=context,
            correlation_id=self._correlation_id,
            parent_id=self._parent_id,
            user=self._user
        )
        self._completed = True
        self._cleanup()
    
    def _cleanup(self) -> None:
        """清理上下文"""
        if self._record_id in self._context_stack:
            self._context_stack.remove(self._record_id)
    
    def __enter__(self) -> 'OperationSpan':
        return self.start()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._completed:
            if exc_val:
                self.failure(exc_val)
            else:
                self.success()
