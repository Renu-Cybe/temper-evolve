"""
Temper Tools 模块
学习 Codong 的风格，工具分组管理
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from ..core.errors import error, is_error

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
        return error(
            "E3001_TOOL_UNKNOWN",
            f"未知工具: {tool_name}",
            fix=f"可用工具: {', '.join(TOOLS.keys())}",
            retryable=False
        )

    tool = TOOLS[tool_name]
    return tool(**kwargs)


def call_chain(chain):
    """
    串行执行工具链

    Args:
        chain: 工具列表，每个工具是 {"tool": "name", "args": {...}}

    Returns:
        结果列表，如果出错则返回错误信息
    """
    results = []
    for idx, tool_spec in enumerate(chain):
        tool_name = tool_spec.get("tool")
        tool_args = tool_spec.get("args", {})

        result = call(tool_name, **tool_args)
        results.append(result)

        # 串行模式：出错停止
        if is_error(result):
            return error(
                "E3002_CHAIN_STOPPED",
                f"工具链在第 {idx+1} 步停止",
                fix=f"前 {idx} 个工具已执行，第 {idx+1} 个工具 '{tool_name}' 失败",
                retryable=True,
                details={
                    "completed": idx,
                    "failed_at": idx + 1,
                    "failed_tool": tool_name,
                    "results_so_far": results
                }
            )

    return {"ok": True, "results": results, "count": len(results)}


def call_parallel(chain):
    """
    并行执行工具链

    Args:
        chain: 工具列表，每个工具是 {"tool": "name", "args": {...}}

    Returns:
        结果列表（保持原始顺序）
    """
    def execute_tool(idx_tool):
        idx, tool_spec = idx_tool
        tool_name = tool_spec.get("tool")
        tool_args = tool_spec.get("args", {})
        result = call(tool_name, **tool_args)
        return idx, result

    # 并行执行
    with ThreadPoolExecutor(max_workers=min(len(chain), 8)) as executor:
        futures = {executor.submit(execute_tool, (i, tool)): i
                   for i, tool in enumerate(chain)}

        results = [None] * len(chain)
        for future in as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    # 检查是否有错误
    errors = [r for r in results if is_error(r)]
    if errors:
        return error(
            "E3003_PARALLEL_PARTIAL_FAIL",
            f"并行工具链部分失败: {len(errors)}/{len(results)} 个工具出错",
            fix="检查失败的工具参数",
            retryable=True,
            details={
                "total": len(results),
                "failed": len(errors),
                "results": results
            }
        )

    return {"ok": True, "results": results, "count": len(results)}
