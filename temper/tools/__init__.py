#!/usr/bin/env python3
"""
🔧 Temper Tools - 工具系统

提供文件系统、命令执行等基础工具
"""

import os
import json
import subprocess
from pathlib import Path

from temper.core import ok, err, is_error, unwrap, ErrorCode


def fs_read(path: str, encoding: str = 'utf-8') -> dict:
    """读取文件内容"""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return err(ErrorCode.FILE_NOT_FOUND, f"文件不存在: {path}", {"path": path})
        if not file_path.is_file():
            return err(ErrorCode.PATH_IS_NOT_FILE, f"路径不是文件: {path}", {"path": path})
        
        content = file_path.read_text(encoding=encoding)
        return ok(content)
    except Exception as e:
        return err(ErrorCode.FILE_READ_ERROR, f"读取文件失败: {path} - {str(e)}")


def fs_write(path: str, content: str, encoding: str = 'utf-8') -> dict:
    """写入文件内容"""
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return ok({"path": str(file_path), "size": len(content)})
    except Exception as e:
        return err(ErrorCode.FILE_WRITE_ERROR, f"写入文件失败: {path} - {str(e)}")


def fs_edit(path: str, old_string: str, new_string: str) -> dict:
    """编辑文件内容（替换）"""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return err(ErrorCode.FILE_NOT_FOUND, f"文件不存在: {path}")
        
        content = file_path.read_text(encoding='utf-8')
        if old_string not in content:
            return err(ErrorCode.VALIDATION_ERROR, f"未找到要替换的内容", {"path": path})
        
        new_content = content.replace(old_string, new_string, 1)
        file_path.write_text(new_content, encoding='utf-8')
        return ok({"path": str(file_path), "replaced": True})
    except Exception as e:
        return err(ErrorCode.FILE_WRITE_ERROR, f"编辑文件失败: {path} - {str(e)}")


def fs_exists(path: str) -> dict:
    """检查文件/目录是否存在"""
    try:
        file_path = Path(path)
        return ok({
            "exists": file_path.exists(),
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir()
        })
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"检查失败: {path} - {str(e)}")


def fs_list(path: str = ".") -> dict:
    """列出目录内容"""
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return err(ErrorCode.PATH_NOT_EXISTS, f"路径不存在: {path}")
        if not dir_path.is_dir():
            return err(ErrorCode.PATH_IS_NOT_DIRECTORY, f"路径不是目录: {path}")
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "path": str(item),
                "is_file": item.is_file(),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None
            })
        return ok(items)
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"列出目录失败: {path} - {str(e)}")


def fs_read_json(path: str) -> dict:
    """读取 JSON 文件"""
    result = fs_read(path)
    if is_error(result):
        return result
    
    try:
        content = unwrap(result)
        data = json.loads(content)
        return ok(data)
    except json.JSONDecodeError as e:
        return err(ErrorCode.PARSE_ERROR, f"JSON解析失败: {path} - {str(e)}")


def fs_write_json(path: str, data: dict, indent: int = 2) -> dict:
    """写入 JSON 文件"""
    try:
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        return fs_write(path, content)
    except Exception as e:
        return err(ErrorCode.SERIALIZATION_ERROR, f"JSON序列化失败: {str(e)}")


def fs_mkdir(path: str, parents: bool = True) -> dict:
    """创建目录"""
    try:
        dir_path = Path(path)
        dir_path.mkdir(parents=parents, exist_ok=True)
        return ok({"path": str(dir_path), "created": True})
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"创建目录失败: {path} - {str(e)}")


def fs_delete(path: str) -> dict:
    """删除文件或目录"""
    try:
        file_path = Path(path)
        if not file_path.exists():
            return err(ErrorCode.FILE_NOT_FOUND, f"路径不存在: {path}")
        
        if file_path.is_file():
            file_path.unlink()
        else:
            import shutil
            shutil.rmtree(file_path)
        
        return ok({"path": path, "deleted": True})
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"删除失败: {path} - {str(e)}")


def shell_run(cmd: str, cwd: str = None, timeout: int = 60) -> dict:
    """执行 shell 命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return ok({
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        })
    except subprocess.TimeoutExpired:
        return err(ErrorCode.OPERATION_TIMEOUT, f"命令超时: {cmd}", {"timeout": timeout})
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"命令执行失败: {cmd} - {str(e)}")


def call(tool_name: str, **kwargs) -> dict:
    """
    调用指定工具
    
    Args:
        tool_name: 工具名称（如 "fs.read", "shell.run"）
        **kwargs: 工具参数
        
    Returns:
        Codong 风格结果
    """
    tools = {
        "fs.read": fs_read,
        "fs.write": fs_write,
        "fs.edit": fs_edit,
        "fs.exists": fs_exists,
        "fs.list": fs_list,
        "fs.read_json": fs_read_json,
        "fs.write_json": fs_write_json,
        "fs.mkdir": fs_mkdir,
        "fs.delete": fs_delete,
        "shell.run": shell_run,
    }
    
    if tool_name not in tools:
        return err(ErrorCode.OPERATION_NOT_SUPPORTED, f"未知工具: {tool_name}")
    
    try:
        return tools[tool_name](**kwargs)
    except Exception as e:
        return err(ErrorCode.OPERATION_FAILED, f"工具调用失败: {tool_name} - {str(e)}")


# 工具注册表
TOOLS = {
    "fs.read": "读取文件内容",
    "fs.write": "写入文件内容",
    "fs.edit": "编辑文件内容",
    "fs.exists": "检查文件是否存在",
    "fs.list": "列出目录内容",
    "fs.read_json": "读取 JSON 文件",
    "fs.write_json": "写入 JSON 文件",
    "fs.mkdir": "创建目录",
    "fs.delete": "删除文件或目录",
    "shell.run": "执行 shell 命令",
}


def call_chain(chain: list) -> dict:
    """
    串行调用工具链
    
    Args:
        chain: 工具调用链，每个元素为 {"tool": str, "args": dict}
        
    Returns:
        Codong 风格结果
    """
    results = []
    for item in chain:
        tool_name = item.get("tool")
        args = item.get("args", {})
        result = call(tool_name, **args)
        results.append({"tool": tool_name, "result": result})
        if is_error(result):
            return err(ErrorCode.WORKFLOW_EXECUTION_ERROR, 
                      f"工具链执行失败: {tool_name}", 
                      {"results": results})
    return ok(results)


def call_parallel(chain: list) -> dict:
    """
    并行调用工具链
    
    Args:
        chain: 工具调用链
        
    Returns:
        Codong 风格结果
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = {}
    with ThreadPoolExecutor(max_workers=len(chain)) as executor:
        futures = {}
        for i, item in enumerate(chain):
            tool_name = item.get("tool")
            args = item.get("args", {})
            future = executor.submit(call, tool_name, **args)
            futures[future] = i
        
        for future in as_completed(futures):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                results[i] = err(ErrorCode.OPERATION_FAILED, str(e))
    
    # 按顺序返回结果
    ordered_results = [results[i] for i in sorted(results.keys())]
    return ok(ordered_results)


__all__ = [
    "fs_read", "fs_write", "fs_edit", "fs_exists", "fs_list",
    "fs_read_json", "fs_write_json", "fs_mkdir", "fs_delete",
    "shell_run", "call", "call_chain", "call_parallel", "TOOLS"
]
