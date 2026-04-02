"""
Result 类型 - Codong 风格的错误处理

遵循铁三角原则：
- 信任：显式错误处理，不隐藏异常
- 复利：统一的错误处理模式
- 杠杆：可扩展的错误类型

使用示例：
    def divide(a: int, b: int) -> Result[float]:
        if b == 0:
            return err(ErrorCode.VALIDATION_ERROR, "Cannot divide by zero")
        return ok(a / b)
    
    result = divide(10, 2)
    if is_ok(result):
        print(f"结果: {unwrap(result)}")
    else:
        print(f"错误: {result.error}")
"""

from typing import TypeVar, Generic, Union, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

T = TypeVar('T')
E = TypeVar('E')
R = TypeVar('R')


class ErrorCode(Enum):
    """错误代码枚举
    
    按模块分类的错误代码，便于错误追踪和处理
    """
    # 系统级错误
    SYSTEM_ERROR = "system_error"
    CONFIG_ERROR = "config_error"
    INITIALIZATION_ERROR = "initialization_error"
    
    # 运行时错误
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    CANCELLED = "cancelled"
    
    # 业务错误
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    ALREADY_EXISTS = "already_exists"
    
    # 自感知错误
    HEALTH_CHECK_FAILED = "health_check_failed"
    METRIC_COLLECTION_FAILED = "metric_collection_failed"
    
    # 自适应错误
    TUNING_FAILED = "tuning_failed"
    OPTIMIZATION_FAILED = "optimization_failed"
    
    # 自组织错误
    WORKFLOW_ERROR = "workflow_error"
    DEPENDENCY_ERROR = "dependency_error"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    
    # 自编译错误
    REPAIR_FAILED = "repair_failed"
    GENERATION_FAILED = "generation_failed"
    HOTLOAD_FAILED = "hotload_failed"
    VALIDATION_FAILED = "validation_failed"


@dataclass(frozen=True)
class Error:
    """错误类型
    
    不可变的数据类，确保错误对象线程安全且可哈希
    
    Attributes:
        code: 错误代码，用于程序化处理
        message: 人类可读的错误信息
        context: 额外的上下文信息
        cause: 导致此错误的原始错误（链式错误）
    """
    code: ErrorCode
    message: str
    context: dict = None
    cause: Optional['Error'] = None
    
    def __post_init__(self):
        if self.context is None:
            object.__setattr__(self, 'context', {})
    
    def with_context(self, **kwargs) -> 'Error':
        """添加上下文信息，返回新的错误对象"""
        new_context = {**self.context, **kwargs}
        return Error(self.code, self.message, new_context, self.cause)
    
    def with_cause(self, cause: 'Error') -> 'Error':
        """设置错误原因，返回新的错误对象"""
        return Error(self.code, self.message, self.context, cause)
    
    def __str__(self) -> str:
        parts = [f"[{self.code.value}] {self.message}"]
        if self.context:
            parts.append(f"context: {self.context}")
        if self.cause:
            parts.append(f"caused by: {self.cause}")
        return " | ".join(parts)
    
    def to_dict(self) -> dict:
        """转换为字典，便于序列化"""
        return {
            'code': self.code.value,
            'message': self.message,
            'context': self.context,
            'cause': self.cause.to_dict() if self.cause else None
        }


@dataclass(frozen=True)
class Ok(Generic[T]):
    """成功结果容器"""
    value: T
    
    def is_ok(self) -> bool:
        return True
    
    def is_error(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        return self.value
    
    def map(self, f: Callable[[T], 'Result']) -> 'Result':
        """映射成功值"""
        return f(self.value)
    
    def map_error(self, f: Callable) -> 'Result[T]':
        """错误处理时忽略，返回自身"""
        return self
    
    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@dataclass(frozen=True)
class Err(Generic[E]):
    """错误结果容器"""
    error: Error
    
    def is_ok(self) -> bool:
        return False
    
    def is_error(self) -> bool:
        return True
    
    def unwrap(self) -> None:
        raise RuntimeError(f"Called unwrap on Err: {self.error}")
    
    def unwrap_or(self, default: T) -> T:
        return default
    
    def map(self, f: Callable) -> 'Result':
        """成功处理时忽略，返回自身"""
        return self
    
    def map_error(self, f: Callable[[Error], 'Result']) -> 'Result':
        """映射错误值"""
        return f(self.error)
    
    def __repr__(self) -> str:
        return f"Err({self.error!r})"


# Result 类型别名 - 成功类型T，错误类型固定为Error
Result = Union[Ok[T], Err[Error]]


# ============ 便捷函数 ============

def ok(value: T) -> Result[T]:
    """创建成功结果"""
    return Ok(value)


def err(code: ErrorCode, message: str, **context) -> Result[Any]:
    """创建错误结果"""
    return Err(Error(code, message, context))


def from_exception(e: Exception, code: ErrorCode = ErrorCode.SYSTEM_ERROR) -> Result[Any]:
    """从异常创建错误结果"""
    return Err(Error(
        code=code,
        message=str(e),
        context={'exception_type': type(e).__name__}
    ))


def is_ok(result: Result) -> bool:
    """检查结果是否成功"""
    return isinstance(result, Ok)


def is_error(result: Result) -> bool:
    """检查结果是否错误"""
    return isinstance(result, Err)


def unwrap(result: Result[T]) -> T:
    """解包结果，错误时抛出异常"""
    if isinstance(result, Ok):
        return result.value
    raise RuntimeError(f"Cannot unwrap Err: {result.error}")


def unwrap_or(result: Result[T], default: T) -> T:
    """解包结果或返回默认值"""
    if isinstance(result, Ok):
        return result.value
    return default


def unwrap_or_else(result: Result[T], f: Callable[[Error], T]) -> T:
    """解包结果或使用函数计算默认值"""
    if isinstance(result, Ok):
        return result.value
    return f(result.error)


def map_result(result: Result[T], 
               f: Callable[[T], R]) -> Result[R]:
    """映射成功结果"""
    if isinstance(result, Ok):
        return Ok(f(result.value))
    return result


def flat_map(result: Result[T],
             f: Callable[[T], Result[R]]) -> Result[R]:
    """扁平映射（避免嵌套 Result）"""
    if isinstance(result, Ok):
        return f(result.value)
    return result


def try_catch(f: Callable[[], T], 
              code: ErrorCode = ErrorCode.SYSTEM_ERROR) -> Result[T]:
    """包装可能抛出异常的函数"""
    try:
        return Ok(f())
    except Exception as e:
        return Err(Error(
            code=code,
            message=str(e),
            context={'exception_type': type(e).__name__}
        ))
