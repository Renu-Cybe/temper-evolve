#!/usr/bin/env python3
"""
🛡️ Temper Validators - 安全检查层

基于 Claude Code 源码的 23 个安全检查点设计

使用方法:
    from temper.validators import validate_command, validate_path, validate_config

    validate_command("rm -rf")  # 会抛出 SecurityError
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re


# ============================================================
# 错误类型定义（统一错误处理）
# ============================================================

@dataclass
class TemperError:
    """统一错误格式（Codong 风格 + 修复建议）"""
    ok: bool = False
    error: str = ""
    message: str = ""
    suggestion: str = ""  # 新增：修复建议
    
    @classmethod
    def success(cls, value=None):
        return {"ok": True, "value": value}
    
    @classmethod
    def fail(cls, error: str, message: str, suggestion: str = ""):
        return {
            "ok": False,
            "error": error,
            "message": message,
            "suggestion": suggestion
        }


class SecurityError(Exception):
    """安全检查失败错误"""
    def __init__(self, code: str, message: str, suggestion: str = ""):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"[{code}] {message}\n建议: {suggestion}")


# ============================================================
# 错误码定义（基于 Claude Code 源码）
# ============================================================

ERROR_CODES = {
    # 安全相关
    'ESEC001': '危险命令检测',
    'ESEC002': '链式操作符禁止',
    'ESEC003': '反引号命令注入',
    'ESEC004': '路径遍历风险',
    'ESEC005': '权限不足',
    
    # 输入验证
    'EINPUT01': '输入长度超限',
    'EINPUT02': '非法字符检测',
    'EINPUT03': '格式验证失败',
    
    # 配置验证
    'ECONFIG01': '配置项缺失',
    'ECONFIG02': '配置值类型错误',
    'ECONFIG03': '配置值超出范围',
}


# ============================================================
# 命令验证器（基于 Claude Code 源码）
# ============================================================

# 危险命令黑名单
DANGEROUS_COMMANDS = [
    r'rm\s+-rf',
    r'rm\s+-fr',
    r'sudo\s+',
    r'chmod\s+777',
    r'chown\s+.*:.*',
    r'iptables',
    r'kill\s+-9\s+1',
    r'format',
    r'fdisk',
    r'mkfs',
]

# 链式操作符
CHAIN_OPERATORS = ['|', '&&', '||', ';', '\n', '`', '$(', '${']


def validate_command(command: str, allow_chains: bool = False) -> Tuple[bool, List[str]]:
    """
    验证命令安全性（基于 Claude Code 源码）
    
    Args:
        command: 待执行的命令
        allow_chains: 是否允许链式操作符
    
    Returns:
        (is_safe, warnings): 是否安全 + 警告列表
    
    Raises:
        SecurityError: 命令包含危险操作
    """
    warnings = []
    
    # 1. 检查危险命令
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            raise SecurityError(
                code="ESEC001",
                message=f"命令包含危险操作: {pattern}",
                suggestion="使用安全的替代方案，如移动到 trash 而非 rm -rf"
            )
    
    # 2. 检查链式操作符
    if not allow_chains:
        for op in CHAIN_OPERATORS:
            if op in command:
                raise SecurityError(
                    code="ESEC002",
                    message=f"命令包含链式操作符: {op}",
                    suggestion="拆分为独立命令执行，或显式设置 allow_chains=True"
                )
    
    # 3. 检查反引号注入
    if '`' in command:
        raise SecurityError(
            code="ESEC003",
            message="命令包含反引号命令注入",
            suggestion="使用 $() 替代反引号，或直接避免命令嵌套"
        )
    
    return True, warnings


# ============================================================
# 路径验证器（防止路径遍历）
# ============================================================

def validate_path(path: str, base_dir: str = None, allow_create: bool = False) -> dict:
    """
    验证路径安全性
    
    Args:
        path: 待验证的路径
        base_dir: 基准目录（路径必须在此目录下）
        allow_create: 是否允许创建新路径
    
    Returns:
        Codong 风格结果
    """
    import os
    
    # 1. 路径遍历检查
    if '..' in path:
        return TemperError.fail(
            error="ESEC004",
            message=f"路径包含遍历字符: ..",
            suggestion="使用绝对路径或确保路径在允许范围内"
        )
    
    # 2. 空字节注入
    if '\x00' in path:
        return TemperError.fail(
            error="ESEC004",
            message="路径包含空字节注入",
            suggestion="清理输入，移除空字节字符"
        )
    
    # 3. 基准目录检查
    if base_dir:
        real_path = os.path.realpath(path)
        real_base = os.path.realpath(base_dir)
        if not real_path.startswith(real_base):
            return TemperError.fail(
                error="ESEC004",
                message=f"路径超出基准目录: {base_dir}",
                suggestion=f"确保路径在 {base_dir} 目录下"
            )
    
    return TemperError.success(path)


# ============================================================
# 配置验证器（EvolverConfig 专用）
# ============================================================

def validate_evolver_config(config: dict) -> dict:
    """
    验证 EvolverConfig 配置
    
    Args:
        config: 配置字典
    
    Returns:
        Codong 风格结果
    """
    # 必需字段
    required_fields = [
        'self_check_interval',
        'adapt_interval',
        'repair_check_interval',
    ]
    
    for field in required_fields:
        if field not in config:
            return TemperError.fail(
                error="ECONFIG01",
                message=f"缺少必需配置项: {field}",
                suggestion=f"添加配置项: {field}"
            )
    
    # 类型检查
    int_fields = required_fields
    for field in int_fields:
        if not isinstance(config.get(field), int):
            return TemperError.fail(
                error="ECONFIG02",
                message=f"配置项 {field} 类型错误，应为 int",
                suggestion=f"设置 {field} 为整数值（秒）"
            )
    
    # 范围检查
    if config.get('self_check_interval', 0) < 10:
        return TemperError.fail(
            error="ECONFIG03",
            message="self_check_interval 不能小于 10 秒",
            suggestion="设置 self_check_interval >= 10"
        )
    
    if config.get('adapt_interval', 0) < 60:
        return TemperError.fail(
            error="ECONFIG03",
            message="adapt_interval 不能小于 60 秒",
            suggestion="设置 adapt_interval >= 60"
        )
    
    return TemperError.success(config)


# ============================================================
# 输入验证器（通用）
# ============================================================

def validate_input(value: str, max_length: int = 1000, 
                   allowed_chars: str = None) -> dict:
    """
    通用输入验证
    
    Args:
        value: 待验证的字符串
        max_length: 最大长度
        allowed_chars: 允许的字符集（正则表达式）
    
    Returns:
        Codong 风格结果
    """
    # 1. 长度检查
    if len(value) > max_length:
        return TemperError.fail(
            error="EINPUT01",
            message=f"输入长度超限: {len(value)} > {max_length}",
            suggestion=f"缩短输入内容至 {max_length} 字符以内"
        )
    
    # 2. 危险字符检查
    dangerous_chars = ['<', '>', '"', "'", ';', '&', '|', '`', '$']
    found = [c for c in dangerous_chars if c in value]
    if found:
        return TemperError.fail(
            error="EINPUT02",
            message=f"输入包含危险字符: {found}",
            suggestion="移除或转义这些字符"
        )
    
    # 3. 字符集检查
    if allowed_chars and not re.match(allowed_chars, value):
        return TemperError.fail(
            error="EINPUT03",
            message="输入格式验证失败",
            suggestion=f"确保输入符合格式: {allowed_chars}"
        )
    
    return TemperError.success(value)