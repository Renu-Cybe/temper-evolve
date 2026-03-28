"""
Temper 类型验证 - 学习 Codong 的可选类型注解
"""

def validate_path(path, must_exist=False):
    """验证路径参数"""
    if not isinstance(path, str):
        return {
            "ok": False,
            "error": "E1002_PATH_INVALID",
            "message": f"路径必须是字符串，收到 {type(path).__name__}",
            "fix": "使用字符串作为路径，例如 'file.txt' 或 '/path/to/file'"
        }
    if not path:
        return {
            "ok": False,
            "error": "E1002_PATH_INVALID",
            "message": "路径不能为空",
            "fix": "提供有效的文件路径"
        }
    return {"ok": True, "value": path}

def validate_string(content, name="content"):
    """验证字符串参数"""
    if not isinstance(content, str):
        return {
            "ok": False,
            "error": "E2003_TYPE_INVALID",
            "message": f"{name} 必须是字符串，收到 {type(content).__name__}",
            "fix": f"确保 {name} 是字符串类型"
        }
    return {"ok": True, "value": content}

def validate_command(cmd):
    """验证命令参数"""
    if not isinstance(cmd, str):
        return {
            "ok": False,
            "error": "E5003_COMMAND_INVALID",
            "message": f"命令必须是字符串，收到 {type(cmd).__name__}",
            "fix": "使用字符串作为 shell 命令"
        }
    if not cmd.strip():
        return {
            "ok": False,
            "error": "E5003_COMMAND_INVALID",
            "message": "命令不能为空",
            "fix": "提供有效的 shell 命令"
        }
    return {"ok": True, "value": cmd}
