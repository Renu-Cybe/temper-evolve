"""
Temper  - Codong 风格的错误系统

学习 Codong 的 `?` 操作符思想，结构化错误处理
"""

class TemperError(dict):
    """Codong 风格的结构化错误"""

    def __init__(self, code, message, fix=None, retryable=False):
        super().__init__({
            "error": code,
            "message": message,
            "fix": fix or "",
            "retry": retryable,
            "ok": False
        })

    def __bool__(self):
        return False

    def __repr__(self):
        return f"E:{self['error']} - {self['message']}"


class TemperOk(dict):
    """成功结果包装"""""

    def __init__(self, value):
        if isinstance(value, dict):
            super().__init__(value)
        else:
            super().__init__({"value": value, "ok": True})

    def __bool__(self):
        return True

# 预定义错误代码（学习 Codong 风格）
ERRORS = {
    "E1001_FILE_NOT_FOUND": "文件不存在",
    "E1002_PATH_INVALID": "路径无效",
    "E1003_PERMISSION_DENIED": "权限拒绝",
    "E2001_EDIT_NO_MATCH": "找不到匹配内容",
    "E2002_SYNTAX_ERROR": "语法错误",
    "E3001_TOOL_UNKNOWN": "未知工具",
    "E3002_JSON_INVALID": "JSON 解析失败",
    "E4001_LLM_ERROR": "LLM 调用失败",
    "E5001_EXEC_TIMEOUT": "执行超时",
    "E5002_EXEC_FAILED": "执行失败",
}

def error(code, message=None, fix=None, retryable=False):
    """创建错误"""
    if code in ERRORS and message is None:
        message = ERRORS[code]
    return TemperError(code, message, fix, retryable)

def ok(value):
    """包装成功结果"""
    return TemperOk(value)

def is_ok(result):
    """检查是否成功"""
    if isinstance(result, dict):
        return result.get("ok", False)
    return True

def is_error(result):
    """检查是否错误"""
    if isinstance(result, dict):
        return not result.get("ok", True)
    return False

def unwrap(result, default=None):
    """解包结果，错误则返回默认值"""
    if is_ok(result):
        return result.get("value", result)
    return default
