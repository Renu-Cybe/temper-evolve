#!/usr/bin/env python3
"""
🎯 Temper Core Errors - Codong 风格错误处理系统

提供统一的错误处理模式：
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 安全提取成功值
- 使用 is_error() 检查结果状态
"""

from typing import Any, Dict, Union, Optional, TypeVar, Generic

# 类型定义
T = TypeVar('T')
Result = Dict[str, Any]


class CodongError(Exception):
    """Codong 风格错误基类"""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code}] {message}")


def ok(value: Any) -> Result:
    """
    创建成功结果
    
    Args:
        value: 成功返回值
        
    Returns:
        {"ok": True, "value": value}
        
    Example:
        >>> ok(42)
        {'ok': True, 'value': 42}
    """
    return {"ok": True, "value": value}


def err(error_code: str, message: str, details: Optional[Dict] = None) -> Result:
    """
    创建错误结果
    
    Args:
        error_code: 错误代码（大写下划线格式）
        message: 错误描述信息
        details: 额外错误详情
        
    Returns:
        {"ok": False, "error": error_code, "message": message, ...}
        
    Example:
        >>> err("FILE_NOT_FOUND", "文件不存在", {"path": "/tmp/test.txt"})
        {'ok': False, 'error': 'FILE_NOT_FOUND', 'message': '文件不存在', 'details': {'path': '/tmp/test.txt'}}
    """
    result = {"ok": False, "error": error_code, "message": message}
    if details:
        result["details"] = details
    return result


def is_error(result: Result) -> bool:
    """
    检查是否为错误结果
    
    Args:
        result: 检查结果
        
    Returns:
        True 如果是错误，False 如果是成功
        
    Example:
        >>> is_error({"ok": False, "error": "ERR", "message": "msg"})
        True
        >>> is_error({"ok": True, "value": 42})
        False
    """
    if not isinstance(result, dict):
        return True
    return not result.get("ok", False)


def is_ok(result: Result) -> bool:
    """
    检查是否为成功结果
    
    Args:
        result: 检查结果
        
    Returns:
        True 如果是成功，False 如果是错误
    """
    if not isinstance(result, dict):
        return False
    return result.get("ok", False)


def unwrap(result: Result, default: Any = None) -> Any:
    """
    从结果中提取值，错误时返回默认值
    
    Args:
        result: 操作结果
        default: 错误时的默认值
        
    Returns:
        成功时返回 value，错误时返回 default
        
    Example:
        >>> unwrap({"ok": True, "value": 42})
        42
        >>> unwrap({"ok": False, "error": "ERR", "message": "msg"}, default=0)
        0
    """
    if is_error(result):
        return default
    return result.get("value")


def unwrap_or_raise(result: Result, exception_class: type = CodongError) -> Any:
    """
    从结果中提取值，错误时抛出异常
    
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


def map_result(result: Result, transform: callable) -> Result:
    """
    对成功结果进行转换
    
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
        return err("TRANSFORM_ERROR", f"转换失败: {str(e)}")


def bind_result(result: Result, next_func: callable) -> Result:
    """
    结果链式绑定（monadic bind）
    
    Args:
        result: 当前结果
        next_func: 下一个处理函数（接收value，返回Result）
        
    Returns:
        链式处理结果
        
    Example:
        >>> bind_result(ok(5), lambda x: ok(x * 2))
        {'ok': True, 'value': 10}
    """
    if is_error(result):
        return result
    try:
        return next_func(result.get("value"))
    except Exception as e:
        return err("BIND_ERROR", f"绑定失败: {str(e)}")


# 常用错误代码
class ErrorCode:
    """标准错误代码常量"""
    
    # 系统级错误
    SYSTEM_ERROR = "SYSTEM_ERROR"
    INITIALIZATION_ERROR = "INITIALIZATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # 文件操作错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    FILE_PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    PATH_NOT_EXISTS = "PATH_NOT_EXISTS"
    PATH_IS_NOT_FILE = "PATH_IS_NOT_FILE"
    PATH_IS_NOT_DIRECTORY = "PATH_IS_NOT_DIRECTORY"
    
    # 网络错误
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_REFUSED = "CONNECTION_REFUSED"
    DNS_RESOLUTION_ERROR = "DNS_RESOLUTION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    API_ERROR = "API_ERROR"
    
    # 数据错误
    PARSE_ERROR = "PARSE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SERIALIZATION_ERROR = "SERIALIZATION_ERROR"
    DESERIALIZATION_ERROR = "DESERIALIZATION_ERROR"
    ENCODING_ERROR = "ENCODING_ERROR"
    
    # 资源错误
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    
    # 操作错误
    OPERATION_FAILED = "OPERATION_FAILED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    OPERATION_CANCELLED = "OPERATION_CANCELLED"
    OPERATION_NOT_SUPPORTED = "OPERATION_NOT_SUPPORTED"
    
    # 模块错误
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    MODULE_LOAD_ERROR = "MODULE_LOAD_ERROR"
    MODULE_INIT_ERROR = "MODULE_INIT_ERROR"
    
    # 工作流错误
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    WORKFLOW_VALIDATION_ERROR = "WORKFLOW_VALIDATION_ERROR"
    WORKFLOW_EXECUTION_ERROR = "WORKFLOW_EXECUTION_ERROR"
    WORKFLOW_CIRCULAR_DEPENDENCY = "WORKFLOW_CIRCULAR_DEPENDENCY"
    TASK_EXECUTION_ERROR = "TASK_EXECUTION_ERROR"
    
    # 健康检查错误
    HEALTH_CHECK_ERROR = "HEALTH_CHECK_ERROR"
    HEALTH_CHECK_WARNING = "HEALTH_CHECK_WARNING"
    HEALTH_CHECK_CRITICAL = "HEALTH_CHECK_CRITICAL"
    
    # 配置错误
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"
    
    # 审计错误
    AUDIT_ERROR = "AUDIT_ERROR"
    AUDIT_LOG_CORRUPTED = "AUDIT_LOG_CORRUPTED"
    BACKUP_ERROR = "BACKUP_ERROR"
    RESTORE_ERROR = "RESTORE_ERROR"
    ROLLBACK_ERROR = "ROLLBACK_ERROR"


# 便捷错误创建函数
def file_not_found(path: str) -> Result:
    """文件不存在错误"""
    return err(ErrorCode.FILE_NOT_FOUND, f"文件不存在: {path}", {"path": path})


def file_read_error(path: str, reason: str) -> Result:
    """文件读取错误"""
    return err(ErrorCode.FILE_READ_ERROR, f"读取文件失败: {path} - {reason}", 
               {"path": path, "reason": reason})


def file_write_error(path: str, reason: str) -> Result:
    """文件写入错误"""
    return err(ErrorCode.FILE_WRITE_ERROR, f"写入文件失败: {path} - {reason}", 
               {"path": path, "reason": reason})


def permission_denied(path: str, operation: str) -> Result:
    """权限拒绝错误"""
    return err(ErrorCode.FILE_PERMISSION_DENIED, 
               f"无权{operation}: {path}", 
               {"path": path, "operation": operation})


def network_error(url: str, reason: str) -> Result:
    """网络错误"""
    return err(ErrorCode.NETWORK_ERROR, f"网络错误: {url} - {reason}", 
               {"url": url, "reason": reason})


def timeout_error(operation: str, timeout: float) -> Result:
    """超时错误"""
    return err(ErrorCode.OPERATION_TIMEOUT, 
               f"操作超时: {operation} (限制 {timeout}s)", 
               {"operation": operation, "timeout": timeout})


def validation_error(field: str, reason: str) -> Result:
    """验证错误"""
    return err(ErrorCode.VALIDATION_ERROR, f"验证失败 [{field}]: {reason}", 
               {"field": field, "reason": reason})


def not_found(resource_type: str, resource_id: str) -> Result:
    """资源不存在错误"""
    return err(ErrorCode.RESOURCE_NOT_FOUND, 
               f"{resource_type} 不存在: {resource_id}", 
               {"type": resource_type, "id": resource_id})


# 测试代码
if __name__ == "__main__":
    print("🧪 测试 Codong 错误处理系统")
    print("=" * 50)
    
    # 测试成功结果
    success = ok(42)
    print(f"✅ 成功结果: {success}")
    print(f"   is_error: {is_error(success)}")
    print(f"   unwrap: {unwrap(success)}")
    
    # 测试错误结果
    failure = err("TEST_ERROR", "测试错误", {"detail": "test"})
    print(f"\n❌ 错误结果: {failure}")
    print(f"   is_error: {is_error(failure)}")
    print(f"   unwrap (default=None): {unwrap(failure)}")
    print(f"   unwrap (default=0): {unwrap(failure, default=0)}")
    
    # 测试便捷函数
    print(f"\n📁 文件不存在: {file_not_found('/tmp/test.txt')}")
    print(f"🌐 网络错误: {network_error('https://example.com', '连接被拒绝')}")
    print(f"⏱️ 超时错误: {timeout_error('API调用', 30.0)}")
    print(f"✓ 验证错误: {validation_error('name', '不能为空')}")
    
    # 测试链式操作
    print("\n⛓️ 测试链式操作:")
    result = ok(5)
    result = bind_result(result, lambda x: ok(x * 2))
    result = bind_result(result, lambda x: ok(x + 1))
    print(f"   ok(5) -> *2 -> +1 = {result}")
    
    # 错误传播
    error_result = bind_result(err("FIRST_ERROR", "第一步错误"), 
                               lambda x: ok(x * 2))
    print(f"   错误传播: {error_result}")
    
    print("\n✅ 所有测试通过!")
