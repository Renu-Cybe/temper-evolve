"""
Temper Tools 模块
学习 Codong 的风格，工具分组管理
"""

from . import fs
from . import shell
from . import self as self_tool

# 工具注册表（类似 Codong 的内置模块）
TOOLS = {
    # FS 模块
    "fs.read": fs.read,
    "fs.write": fs.write,
    "fs.edit": fs.edit,
    "fs.exists": fs.exists,
    "fs.list": fs.list_dir,
    "fs.read_json": fs.read_json,

    # Shell 模块
    "shell.run": shell.run,

    # Self 模块（自我进化）
    "self.snapshot": self_tool.snapshot,
    "self.diff": self_tool.diff,
    "self.log": self_tool.log,
    "self.list_snapshots": self_tool.list_snapshots,
}

def call(tool_name, **kwargs):
    """
    调用工具（带错误处理）

    Args:
        tool_name: 工具名，如 "fs.read", "shell.run"
        **kwargs: 工具参数

    Returns:
        工具执行结果
    """
    if tool_name not in TOOLS:
        from ..core.errors import error
        return error(
            "E3001_TOOL_UNKNOWN",
            f"未知工具: {tool_name}",
            fix=f"可用工具: {', '.join(TOOLS.keys())}",
            retryable=False
        )

    tool = TOOLS[tool_name]
    return tool(**kwargs)
