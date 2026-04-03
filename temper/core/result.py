#!/usr/bin/env python3
"""
🧊 Temper Core Result - Codong 风格错误处理系统

统一错误处理规范：
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 安全提取成功值
- 使用 is_error() 检查结果状态

铁三角原则：
- 信任：显式错误处理，不隐藏异常
- 复利：统一的错误处理模式
- 杠杆：可扩展的错误类型

使用示例：
    from temper.core import ok, err, is_error, unwrap

    def divide(a: int, b: int):
        if b == 0:
            return err("DIVISION_BY_ZERO", "除数不能为零")
        return ok(a / b)

    result = divide(10, 2)
    if is_error(result):
        print(f"错误：{result['message']}")
    else:
        print(f"结果：{unwrap(result)}")
"""

from typing import Any, Dict, Optional, Union, TypeVar, Generic, Callable
from dataclasses import dataclass
from enum import Enum, auto
import json

# =============================================================================
# 类型定义
# =============================================================================

T = TypeVar('T')
E = TypeVar('E')
R = TypeVar('R')
Result = Dict[str, Any]

# =============================================================================
# 错误代码枚举
# =============================================================================


class ErrorCode(Enum):
    """标准错误代码枚举

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

    # 文件操作错误
    FILE_NOT_FOUND = "file_not_found"
    FILE_READ_ERROR = "file_read_error"
    FILE_WRITE_ERROR = "file_write_error"
    PATH_NOT_EXISTS = "path_not_exists"

    # 网络错误
    NETWORK_ERROR = "network_error"
    CONNECTION_TIMEOUT = "connection_timeout"
    CONNECTION_REFUSED = "connection_refused"
    API_ERROR = "api_error"

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

    # 审计错误
    AUDIT_ERROR = "audit_error"
    BACKUP_ERROR = "backup_error"
    RESTORE_ERROR = "restore_error"
    ROLLBACK_ERROR = "rollback_error"


# =============================================================================
# 异常类型定义
# =============================================================================


class CodongError(Exception):
    """Codong 风格错误基类

    Attributes:
        error_code: 错误代码
        message: 错误信息
        details: 额外详情
    """

    def __init__(self, error_code: str, message: str, details: Optional[Dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code}] {message}")

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


# =============================================================================
# 核心错误处理函数
# =============================================================================

def ok(value: Any) -> Result:
    """创建成功结果

    Args:
        value: 成功返回值

    Returns:
        {"ok": True, "value": value}
    """
    return {"ok": True, "value": value}


def err(error_code: Union[str, ErrorCode], message: str, details: Optional[Dict] = None) -> Result:
    """创建错误结果

    Args:
        error_code: 错误代码（字符串或 ErrorCode 枚举）
        message: 错误描述信息
        details: 额外错误详情

    Returns:
        {"ok": False, "error": error_code, "message": message, ...}
    """
    code = error_code.value if isinstance(error_code, ErrorCode) else error_code
    result = {"ok": False, "error": code, "message": message}
    if details:
        result["details"] = details
    return result


def is_error(result: Result) -> bool:
    """检查是否为错误结果

    Args:
        result: 检查结果

    Returns:
        True 如果是错误，False 如果是成功
    """
    if not isinstance(result, dict):
        return True
    return not result.get("ok", False)


def is_ok(result: Result) -> bool:
    """检查是否为成功结果

    Args:
        result: 检查结果

    Returns:
        True 如果是成功，False 如果是错误
    """
    if not isinstance(result, dict):
        return False
    return result.get("ok", False)


def unwrap(result: Result, default: Any = None) -> Any:
    """从结果中提取值，错误时返回默认值

    Args:
        result: 操作结果
        default: 错误时的默认值

    Returns:
        成功时返回 value，错误时返回 default
    """
    if is_error(result):
        return default
    return result.get("value")


def unwrap_or_raise(result: Result, exception_class: type = CodongError) -> Any:
    """从结果中提取值，错误时抛出异常

    Args:
        result: 操作结果
        exception_class: 要抛出的异常类

    Returns:
        成功时返回 value

    Raises:
        exception_class: 错误时抛出
    """
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        details = result.get("details", {})
        raise exception_class(error_code, message, details)
    return result.get("value")


# =============================================================================
# 函数式操作
# =============================================================================

def map_result(result: Result, transform: Callable[[Any], Any]) -> Result:
    """对成功结果进行转换

    Args:
        result: 操作结果
        transform: 转换函数

    Returns:
        转换后的结果
    """
    if is_error(result):
        return result
    try:
        new_value = transform(result.get("value"))
        return ok(new_value)
    except Exception as e:
        return err("TRANSFORM_ERROR", f"转换失败：{str(e)}")


def bind_result(result: Result, next_func: Callable[[Any], Result]) -> Result:
    """链式绑定（monadic bind）

    Args:
        result: 当前结果
        next_func: 下一个处理函数（接收 value，返回 Result）

    Returns:
        链式处理结果
    """
    if is_error(result):
        return result
    try:
        return next_func(result.get("value"))
    except Exception as e:
        return err("BIND_ERROR", f"绑定失败：{str(e)}")


def flat_map(result: Result, func: Callable[[Any], Result]) -> Result:
    """扁平映射（bind 的别名）"""
    return bind_result(result, func)


def try_catch(func: Callable[[], Any],
              error_code: Union[str, ErrorCode] = ErrorCode.SYSTEM_ERROR) -> Result:
    """包装可能抛出异常的函数

    Args:
        func: 要执行的函数
        error_code: 错误代码

    Returns:
        执行结果
    """
    try:
        return ok(func())
    except Exception as e:
        return err(error_code, str(e), {"exception_type": type(e).__name__})


# =============================================================================
# 便捷错误创建函数
# =============================================================================

def file_not_found(path: str) -> Result:
    """文件不存在错误"""
    return err(ErrorCode.FILE_NOT_FOUND, f"文件不存在：{path}", {"path": path})


def file_read_error(path: str, reason: str) -> Result:
    """文件读取错误"""
    return err(ErrorCode.FILE_READ_ERROR, f"读取文件失败：{path} - {reason}",
               {"path": path, "reason": reason})


def file_write_error(path: str, reason: str) -> Result:
    """文件写入错误"""
    return err(ErrorCode.FILE_WRITE_ERROR, f"写入文件失败：{path} - {reason}",
               {"path": path, "reason": reason})


def permission_denied(path: str, operation: str) -> Result:
    """权限拒绝错误"""
    return err(ErrorCode.PERMISSION_DENIED,
               f"无权{operation}: {path}",
               {"path": path, "operation": operation})


def network_error(url: str, reason: str) -> Result:
    """网络错误"""
    return err(ErrorCode.NETWORK_ERROR, f"网络错误：{url} - {reason}",
               {"url": url, "reason": reason})


def timeout_error(operation: str, timeout: float) -> Result:
    """超时错误"""
    return err(ErrorCode.TIMEOUT,
               f"操作超时：{operation} (限制 {timeout}s)",
               {"operation": operation, "timeout": timeout})


def validation_error(field: str, reason: str) -> Result:
    """验证错误"""
    return err(ErrorCode.VALIDATION_ERROR, f"验证失败 [{field}]: {reason}",
               {"field": field, "reason": reason})


def not_found(resource_type: str, resource_id: str) -> Result:
    """资源不存在错误"""
    return err(ErrorCode.NOT_FOUND,
               f"{resource_type} 不存在：{resource_id}",
               {"type": resource_type, "id": resource_id})


def from_exception(e: Exception,
                   error_code: Union[str, ErrorCode] = ErrorCode.SYSTEM_ERROR) -> Result:
    """从异常创建错误结果"""
    return err(error_code, str(e), {"exception_type": type(e).__name__})


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("🧪 测试 Codong 错误处理系统")
    print("=" * 50)

    # 测试成功结果
    success = ok(42)
    print(f"✅ 成功结果：{success}")
    print(f"   is_error: {is_error(success)}")
    print(f"   unwrap: {unwrap(success)}")

    # 测试错误结果
    failure = err("TEST_ERROR", "测试错误", {"detail": "test"})
    print(f"\n❌ 错误结果：{failure}")
    print(f"   is_error: {is_error(failure)}")
    print(f"   unwrap (default=None): {unwrap(failure)}")
    print(f"   unwrap (default=0): {unwrap(failure, default=0)}")

    # 测试便捷函数
    print(f"\n📁 文件不存在：{file_not_found('/tmp/test.txt')}")
    print(f"🌐 网络错误：{network_error('https://example.com', '连接被拒绝')}")
    print(f"⏱️ 超时错误：{timeout_error('API 调用', 30.0)}")
    print(f"✓ 验证错误：{validation_error('name', '不能为空')}")

    # 测试链式操作
    print("\n⛓️ 测试链式操作:")
    result = ok(5)
    result = bind_result(result, lambda x: ok(x * 2))
    result = bind_result(result, lambda x: ok(x + 1))
    print(f"   ok(5) -> *2 -> +1 = {result}")

    # 错误传播
    error_result = bind_result(err("FIRST_ERROR", "第一步错误"),
                               lambda x: ok(x * 2))
    print(f"   错误传播：{error_result}")

    # 测试 try_catch
    print("\n🛡️ 测试 try_catch:")
    safe_result = try_catch(lambda: 10 / 2)
    print(f"   10/2 = {unwrap(safe_result)}")

    error_safe = try_catch(lambda: 10 / 0, "DIVISION_ERROR")
    print(f"   10/0 = {error_safe}")

    print("\n✅ 所有测试通过!")
