"""
Temper Tools - Shell 模块
学习 Codong 的 shell 风格，统一命令执行
"""

import subprocess
from ..core.errors import error, ok
from ..core.types import validate_command

def run(cmd, timeout=30):
    """
    执行 shell 命令

    Args:
        cmd: 命令字符串
        timeout: 超时时间（秒）

    Returns:
        成功: {"ok": True, "stdout": "...", "stderr": "...", "code": 0}
        失败: {"ok": False, "error": "E5001_EXEC_TIMEOUT", ...}
    """
    # 验证参数
    validated = validate_command(cmd)
    if not validated["ok"]:
        return validated

    cmd = validated["value"]

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            return ok({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "code": 0
            })
        else:
            return error(
                "E5002_EXEC_FAILED",
                f"命令退出码 {result.returncode}: {result.stderr[:200]}",
                fix="检查命令语法和参数",
                retryable=False
            )

    except subprocess.TimeoutExpired:
        return error(
            "E5001_EXEC_TIMEOUT",
            f"命令执行超时（>{timeout}s）",
            fix="增加 timeout 参数或简化命令",
            retryable=True
        )
    except Exception as e:
        return error(
            "E5002_EXEC_FAILED",
            f"执行失败: {str(e)}",
            fix="检查命令是否可执行",
            retryable=False
        )
