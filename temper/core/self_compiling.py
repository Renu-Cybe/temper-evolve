#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自编译模块 (Self-Compiling Module)

功能:
1. 代码模板系统 - 支持代码模板定义和渲染
2. 运行时代码生成 - 动态生成Python代码
3. 自我修复机制 - 检测并修复代码问题
4. 模块热加载 - 支持运行时模块热更新

信任原则:
- 不得擅自修改用户原始文件
- 所有修改必须通过审计日志记录
- 修改前必须创建备份
- 支持操作回滚

Codong风格错误处理:
- 成功: {"ok": True, "value": 返回值}
- 错误: {"ok": False, "error": "ERROR_CODE", "message": "详细错误信息"}
"""

import ast
import builtins
import hashlib
import importlib
import importlib.util
import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import types
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Codong风格错误处理工具函数
# =============================================================================

def is_error(result: Dict[str, Any]) -> bool:
    """检查结果是否为错误"""
    return not result.get("ok", False)


def unwrap(result: Dict[str, Any]) -> Any:
    """从结果中提取值，如果是错误则抛出异常"""
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def ok(value: Any) -> Dict[str, Any]:
    """创建成功结果"""
    return {"ok": True, "value": value}


def err(error_code: str, message: str) -> Dict[str, Any]:
    """创建错误结果"""
    return {"ok": False, "error": error_code, "message": message}


# =============================================================================
# 审计日志系统
# =============================================================================

@dataclass
class AuditLogEntry:
    """审计日志条目"""
    timestamp: str
    operation: str
    file_path: str
    backup_path: Optional[str]
    details: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class AuditLogger:
    """
    审计日志记录器
    
    记录所有文件修改操作，支持回滚
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化审计日志记录器
        
        Args:
            log_dir: 日志目录，默认为系统临时目录下的temper_audit
        """
        if log_dir is None:
            log_dir = os.path.join(tempfile.gettempdir(), "temper_audit")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = self.log_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        self.log_file = self.log_dir / "audit.log"
        self.entries: List[AuditLogEntry] = []
        self.lock = threading.RLock()
        
        # 加载已有日志
        self._load_log()
    
    def _load_log(self) -> None:
        """加载已有日志"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [AuditLogEntry(**entry) for entry in data]
            except Exception:
                self.entries = []
    
    def _save_log(self) -> None:
        """保存日志到文件"""
        with self.lock:
            data = [
                {
                    "timestamp": entry.timestamp,
                    "operation": entry.operation,
                    "file_path": entry.file_path,
                    "backup_path": entry.backup_path,
                    "details": entry.details,
                    "success": entry.success,
                    "error_message": entry.error_message
                }
                for entry in self.entries
            ]
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    def log(self, operation: str, file_path: str, 
            backup_path: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
            success: bool = True,
            error_message: Optional[str] = None) -> Dict[str, Any]:
        """
        记录操作日志
        
        Args:
            operation: 操作类型
            file_path: 操作的文件路径
            backup_path: 备份文件路径
            details: 详细信息
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            entry = AuditLogEntry(
                timestamp=datetime.now().isoformat(),
                operation=operation,
                file_path=file_path,
                backup_path=backup_path,
                details=details or {},
                success=success,
                error_message=error_message
            )
            self.entries.append(entry)
            self._save_log()
        return ok(entry)
    
    def create_backup(self, file_path: str) -> Dict[str, Any]:
        """
        创建文件备份
        
        Args:
            file_path: 要备份的文件路径
            
        Returns:
            Codong风格结果，包含备份路径
        """
        try:
            source = Path(file_path)
            if not source.exists():
                return err("FILE_NOT_FOUND", f"文件不存在: {file_path}")
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
            backup_name = f"{timestamp}_{file_hash}_{source.name}"
            backup_path = self.backup_dir / backup_name
            
            # 复制文件
            shutil.copy2(str(source), str(backup_path))
            
            return ok(str(backup_path))
        except Exception as e:
            return err("BACKUP_FAILED", f"备份失败: {str(e)}")
    
    def rollback(self, entry_index: int = -1) -> Dict[str, Any]:
        """
        回滚操作
        
        Args:
            entry_index: 要回滚的日志条目索引，-1表示最新的一条
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            if not self.entries:
                return err("NO_ENTRIES", "没有可回滚的操作")
            
            entry = self.entries[entry_index]
            
            if not entry.backup_path or not Path(entry.backup_path).exists():
                return err("BACKUP_NOT_FOUND", "备份文件不存在")
            
            try:
                # 恢复备份
                shutil.copy2(entry.backup_path, entry.file_path)
                
                # 记录回滚操作
                self.log(
                    operation="ROLLBACK",
                    file_path=entry.file_path,
                    details={"rolled_back_entry": entry.timestamp},
                    success=True
                )
                
                return ok({
                    "restored_file": entry.file_path,
                    "from_backup": entry.backup_path
                })
            except Exception as e:
                return err("ROLLBACK_FAILED", f"回滚失败: {str(e)}")
    
    def get_history(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取操作历史
        
        Args:
            file_path: 筛选特定文件的历史，None表示所有文件
            
        Returns:
            Codong风格结果
        """
        if file_path:
            entries = [e for e in self.entries if e.file_path == file_path]
        else:
            entries = self.entries
        return ok([{
            "timestamp": e.timestamp,
            "operation": e.operation,
            "file_path": e.file_path,
            "success": e.success,
            "error_message": e.error_message
        } for e in entries])


# =============================================================================
# 代码模板系统
# =============================================================================

@dataclass
class TemplateVariable:
    """模板变量定义"""
    name: str
    var_type: str = "str"  # str, int, float, bool, list, dict, code
    default: Any = None
    required: bool = True
    description: str = ""


class CodeTemplate:
    """
    代码模板类
    
    支持变量插值、条件渲染和循环渲染
    """
    
    # 内置模板库
    BUILTIN_TEMPLATES = {
        "function": '''
def {{name}}({{params}}):
    """
    {{description}}
    """
    {{body}}
''',
        "class": '''
class {{name}}{% if base_class %}({{base_class}}){% endif %}:
    """
    {{description}}
    """
    
    def __init__(self{{init_params}}):
        {{init_body}}
''',
        "method": '''
    def {{name}}(self{{params}}):
        """
        {{description}}
        """
        {{body}}
''',
        "property": '''
    @property
    def {{name}}(self):
        """
        {{description}}
        """
        {{body}}
''',
        "error_handler": '''
def {{name}}(result: Dict[str, Any]) -> bool:
    """
    检查{{name}}结果
    """
    if not result.get("ok", False):
        error_code = result.get("error", "UNKNOWN")
        message = result.get("message", "未知错误")
        {{error_action}}
        return False
    return True
''',
        "codong_function": '''
def {{name}}({{params}}) -> Dict[str, Any]:
    """
    {{description}}
    """
    try:
        {{body}}
        return {"ok": True, "value": {{return_value}}}
    except Exception as e:
        return {"ok": False, "error": "{{error_code}}", "message": str(e)}
'''
    }
    
    def __init__(self, template: str, name: str = "anonymous"):
        """
        初始化代码模板
        
        Args:
            template: 模板字符串或模板名称
            name: 模板名称
        """
        self.name = name
        self.variables: Dict[str, TemplateVariable] = {}
        
        # 如果是内置模板名称，使用内置模板
        if template in self.BUILTIN_TEMPLATES:
            self.template = self.BUILTIN_TEMPLATES[template]
            self.name = template
        else:
            self.template = template
        
        # 解析模板变量
        self._parse_variables()
    
    def _parse_variables(self) -> None:
        """解析模板中的变量"""
        # 匹配 {{variable}} 格式
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, self.template)
        
        for var_name in set(matches):
            self.variables[var_name] = TemplateVariable(
                name=var_name,
                var_type="str",
                required=True
            )
        
        # 匹配 {% if variable %} 条件
        condition_pattern = r'\{%\s*if\s+(\w+)\s*%\}'
        condition_matches = re.findall(condition_pattern, self.template)
        
        for var_name in set(condition_matches):
            if var_name not in self.variables:
                self.variables[var_name] = TemplateVariable(
                    name=var_name,
                    var_type="bool",
                    default=False,
                    required=False
                )
    
    def define_variable(self, name: str, var_type: str = "str", 
                       default: Any = None, required: bool = True,
                       description: str = "") -> Dict[str, Any]:
        """
        定义模板变量
        
        Args:
            name: 变量名
            var_type: 变量类型
            default: 默认值
            required: 是否必需
            description: 描述
            
        Returns:
            Codong风格结果
        """
        self.variables[name] = TemplateVariable(
            name=name,
            var_type=var_type,
            default=default,
            required=required,
            description=description
        )
        return ok(True)
    
    def render(self, **kwargs) -> Dict[str, Any]:
        """
        渲染模板
        
        Args:
            **kwargs: 模板变量值
            
        Returns:
            Codong风格结果，包含渲染后的代码
        """
        try:
            result = self.template
            
            # 处理条件渲染 {% if variable %}...{% endif %}
            result = self._process_conditions(result, kwargs)
            
            # 处理循环渲染 {% for item in items %}...{% endfor %}
            result = self._process_loops(result, kwargs)
            
            # 处理变量插值 {{variable}}
            for var_name, var_def in self.variables.items():
                if var_name in kwargs:
                    value = kwargs[var_name]
                elif var_def.default is not None:
                    value = var_def.default
                elif var_def.required:
                    return err("MISSING_VARIABLE", f"缺少必需变量: {var_name}")
                else:
                    value = ""
                
                # 转换值为字符串
                if var_def.var_type == "code":
                    value = self._format_code(value)
                elif var_def.var_type == "list":
                    value = ", ".join(str(v) for v in value)
                elif var_def.var_type == "dict":
                    value = json.dumps(value, ensure_ascii=False)
                else:
                    value = str(value)
                
                result = result.replace(f"{{{{{var_name}}}}}", value)
            
            return ok(result)
        except Exception as e:
            return err("RENDER_FAILED", f"模板渲染失败: {str(e)}")
    
    def _process_conditions(self, template: str, context: Dict[str, Any]) -> str:
        """处理条件渲染"""
        pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'
        
        def replace_condition(match):
            var_name = match.group(1)
            content = match.group(2)
            condition = context.get(var_name, False)
            
            # 处理 {% else %}
            if '{% else %}' in content:
                true_part, false_part = content.split('{% else %}', 1)
                return true_part if condition else false_part
            
            return content if condition else ""
        
        return re.sub(pattern, replace_condition, template, flags=re.DOTALL)
    
    def _process_loops(self, template: str, context: Dict[str, Any]) -> str:
        """处理循环渲染"""
        pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'
        
        def replace_loop(match):
            item_name = match.group(1)
            list_name = match.group(2)
            content = match.group(3)
            
            items = context.get(list_name, [])
            if not isinstance(items, list):
                return ""
            
            results = []
            for item in items:
                item_context = {**context, item_name: item}
                item_content = content
                
                # 处理循环内的变量
                for key, value in item_context.items():
                    item_content = item_content.replace(f"{{{{{key}}}}}", str(value))
                
                results.append(item_content)
            
            return "\n".join(results)
        
        return re.sub(pattern, replace_loop, template, flags=re.DOTALL)
    
    def _format_code(self, code: str) -> str:
        """格式化代码块，保持缩进"""
        lines = code.strip().split('\n')
        if len(lines) <= 1:
            return code.strip()
        
        # 计算最小缩进
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return code.strip()
        
        # 移除公共缩进
        return '\n'.join(line[min_indent:] for line in lines)
    
    def get_variables(self) -> Dict[str, Any]:
        """获取模板变量定义"""
        return ok({
            name: {
                "type": var.var_type,
                "default": var.default,
                "required": var.required,
                "description": var.description
            }
            for name, var in self.variables.items()
        })
    
    @classmethod
    def get_builtin_templates(cls) -> Dict[str, Any]:
        """获取所有内置模板名称"""
        return ok(list(cls.BUILTIN_TEMPLATES.keys()))


# =============================================================================
# 代码生成器
# =============================================================================

class CodeGenerator:
    """
    代码生成器
    
    支持动态生成Python代码，包括函数、类、模块等
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        初始化代码生成器
        
        Args:
            audit_logger: 审计日志记录器
        """
        self.audit_logger = audit_logger or AuditLogger()
        self.generated_modules: Dict[str, types.ModuleType] = {}
        self.templates: Dict[str, CodeTemplate] = {}
        self.lock = threading.RLock()
        
        # 加载内置模板
        self._load_builtin_templates()
    
    def _load_builtin_templates(self) -> None:
        """加载内置模板"""
        for name in CodeTemplate.BUILTIN_TEMPLATES.keys():
            self.templates[name] = CodeTemplate(name)
    
    def register_template(self, name: str, template: Union[str, CodeTemplate]) -> Dict[str, Any]:
        """
        注册自定义模板
        
        Args:
            name: 模板名称
            template: 模板字符串或CodeTemplate对象
            
        Returns:
            Codong风格结果
        """
        try:
            if isinstance(template, str):
                self.templates[name] = CodeTemplate(template, name)
            elif isinstance(template, CodeTemplate):
                self.templates[name] = template
            else:
                return err("INVALID_TEMPLATE", "模板必须是字符串或CodeTemplate对象")
            return ok(True)
        except Exception as e:
            return err("REGISTER_FAILED", f"注册模板失败: {str(e)}")
    
    def generate_function(self, name: str, params: List[Dict[str, Any]], 
                         body: str, description: str = "",
                         decorators: Optional[List[str]] = None,
                         return_type: Optional[str] = None) -> Dict[str, Any]:
        """
        生成函数代码
        
        Args:
            name: 函数名
            params: 参数列表，每个参数是{"name": str, "type": str, "default": Any}
            body: 函数体
            description: 函数描述
            decorators: 装饰器列表
            return_type: 返回类型注解
            
        Returns:
            Codong风格结果，包含生成的代码
        """
        try:
            # 构建参数字符串
            param_strs = []
            for p in params:
                p_str = p["name"]
                if p.get("type"):
                    p_str += f': {p["type"]}'
                if "default" in p:
                    default_val = p["default"]
                    if isinstance(default_val, str):
                        default_val = f'"{default_val}"'
                    p_str += f' = {default_val}'
                param_strs.append(p_str)
            
            params_str = ", ".join(param_strs)
            
            # 构建函数代码
            code_lines = []
            
            # 添加装饰器
            if decorators:
                for dec in decorators:
                    code_lines.append(f"@{dec}")
            
            # 添加函数定义
            return_annotation = f" -> {return_type}" if return_type else ""
            code_lines.append(f"def {name}({params_str}){return_annotation}:")
            
            # 添加文档字符串
            if description:
                code_lines.append(f'    """')
                code_lines.append(f'    {description}')
                code_lines.append(f'    """')
            
            # 添加函数体
            body_lines = body.strip().split('\n')
            for line in body_lines:
                code_lines.append(f"    {line}")
            
            code = '\n'.join(code_lines)
            return ok(code)
        except Exception as e:
            return err("GENERATE_FAILED", f"生成函数失败: {str(e)}")
    
    def generate_class(self, name: str, base_classes: Optional[List[str]] = None,
                      methods: Optional[List[Dict[str, Any]]] = None,
                      attributes: Optional[List[Dict[str, Any]]] = None,
                      description: str = "") -> Dict[str, Any]:
        """
        生成类代码
        
        Args:
            name: 类名
            base_classes: 基类列表
            methods: 方法列表
            attributes: 属性列表
            description: 类描述
            
        Returns:
            Codong风格结果
        """
        try:
            code_lines = []
            
            # 类定义
            bases = f"({', '.join(base_classes)})" if base_classes else ""
            code_lines.append(f"class {name}{bases}:")
            
            # 文档字符串
            if description:
                code_lines.append(f'    """')
                code_lines.append(f'    {description}')
                code_lines.append(f'    """')
            
            # __init__方法
            code_lines.append("")
            code_lines.append("    def __init__(self):")
            
            # 初始化属性
            if attributes:
                for attr in attributes:
                    attr_name = attr["name"]
                    default = attr.get("default", None)
                    if default is not None:
                        if isinstance(default, str):
                            default = f'"{default}"'
                        code_lines.append(f"        self.{attr_name} = {default}")
                    else:
                        code_lines.append(f"        self.{attr_name} = None")
            else:
                code_lines.append("        pass")
            
            # 添加方法
            if methods:
                for method in methods:
                    method_code = unwrap(self.generate_function(
                        name=method["name"],
                        params=method.get("params", []),
                        body=method.get("body", "pass"),
                        description=method.get("description", ""),
                        decorators=method.get("decorators"),
                        return_type=method.get("return_type")
                    ))
                    # 缩进方法代码
                    indented_method = '\n'.join(
                        f"    {line}" if line.strip() else line
                        for line in method_code.split('\n')
                    )
                    code_lines.append("")
                    code_lines.append(indented_method)
            
            code = '\n'.join(code_lines)
            return ok(code)
        except Exception as e:
            return err("GENERATE_FAILED", f"生成类失败: {str(e)}")
    
    def generate_module(self, name: str, 
                       imports: Optional[List[str]] = None,
                       functions: Optional[List[Dict[str, Any]]] = None,
                       classes: Optional[List[Dict[str, Any]]] = None,
                       code: Optional[str] = None) -> Dict[str, Any]:
        """
        生成模块代码
        
        Args:
            name: 模块名
            imports: 导入语句列表
            functions: 函数字典列表
            classes: 类字典列表
            code: 额外代码
            
        Returns:
            Codong风格结果
        """
        try:
            code_lines = []
            
            # 模块文档字符串
            code_lines.append(f'"""')
            code_lines.append(f'{name} 模块')
            code_lines.append(f'由代码生成器自动生成')
            code_lines.append(f'生成时间: {datetime.now().isoformat()}')
            code_lines.append(f'"""')
            code_lines.append("")
            
            # 导入语句
            if imports:
                for imp in imports:
                    code_lines.append(imp)
                code_lines.append("")
            
            # 生成函数
            if functions:
                for func in functions:
                    func_code = unwrap(self.generate_function(**func))
                    code_lines.append(func_code)
                    code_lines.append("")
            
            # 生成类
            if classes:
                for cls in classes:
                    cls_code = unwrap(self.generate_class(**cls))
                    code_lines.append(cls_code)
                    code_lines.append("")
            
            # 额外代码
            if code:
                code_lines.append(code)
            
            return ok('\n'.join(code_lines))
        except Exception as e:
            return err("GENERATE_FAILED", f"生成模块失败: {str(e)}")
    
    def compile_code(self, code: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        编译代码
        
        Args:
            code: Python代码字符串
            name: 模块名称
            
        Returns:
            Codong风格结果，包含编译后的代码对象
        """
        try:
            # 语法检查
            ast.parse(code)
            
            # 编译代码
            compiled = compile(code, f"<{name or 'generated'}>", 'exec')
            return ok(compiled)
        except SyntaxError as e:
            return err("SYNTAX_ERROR", f"语法错误 (行{e.lineno}): {e.msg}")
        except Exception as e:
            return err("COMPILE_FAILED", f"编译失败: {str(e)}")
    
    def execute_code(self, code: str, context: Optional[Dict[str, Any]] = None,
                    name: Optional[str] = None) -> Dict[str, Any]:
        """
        执行代码
        
        Args:
            code: Python代码字符串
            context: 执行上下文
            name: 模块名称
            
        Returns:
            Codong风格结果
        """
        try:
            # 编译代码
            compiled = unwrap(self.compile_code(code, name))
            
            # 创建执行环境
            exec_context = context or {}
            exec_context.setdefault('__builtins__', builtins)
            
            # 执行代码
            exec(compiled, exec_context)
            
            return ok(exec_context)
        except Exception as e:
            return err("EXECUTE_FAILED", f"执行失败: {str(e)}")
    
    def create_module(self, code: str, module_name: str,
                     file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        创建模块
        
        Args:
            code: 模块代码
            module_name: 模块名称
            file_path: 模块文件路径（可选）
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            try:
                # 创建模块
                module = types.ModuleType(module_name)
                module.__file__ = file_path or f"<generated:{module_name}>"
                
                # 执行代码填充模块
                result = self.execute_code(code, module.__dict__, module_name)
                if is_error(result):
                    return result
                
                # 注册模块
                self.generated_modules[module_name] = module
                sys.modules[module_name] = module
                
                return ok(module)
            except Exception as e:
                return err("CREATE_MODULE_FAILED", f"创建模块失败: {str(e)}")
    
    def save_module(self, module_name: str, file_path: str,
                   create_backup: bool = True) -> Dict[str, Any]:
        """
        保存模块到文件
        
        Args:
            module_name: 模块名称
            file_path: 文件路径
            create_backup: 是否创建备份
            
        Returns:
            Codong风格结果
        """
        try:
            module = self.generated_modules.get(module_name)
            if not module:
                return err("MODULE_NOT_FOUND", f"模块不存在: {module_name}")
            
            # 创建备份
            backup_path = None
            if create_backup and Path(file_path).exists():
                backup_result = self.audit_logger.create_backup(file_path)
                if not is_error(backup_result):
                    backup_path = unwrap(backup_result)
            
            # 获取模块源代码
            if hasattr(module, '__source__'):
                source = module.__source__
            else:
                # 尝试从文件读取
                if hasattr(module, '__file__') and Path(module.__file__).exists():
                    with open(module.__file__, 'r', encoding='utf-8') as f:
                        source = f.read()
                else:
                    return err("NO_SOURCE", "模块没有可用的源代码")
            
            # 写入文件
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(source)
            
            # 记录审计日志
            self.audit_logger.log(
                operation="SAVE_MODULE",
                file_path=file_path,
                backup_path=backup_path,
                details={"module_name": module_name},
                success=True
            )
            
            return ok(file_path)
        except Exception as e:
            return err("SAVE_FAILED", f"保存模块失败: {str(e)}")
    
    def get_module(self, module_name: str) -> Dict[str, Any]:
        """获取生成的模块"""
        module = self.generated_modules.get(module_name)
        if module:
            return ok(module)
        return err("MODULE_NOT_FOUND", f"模块不存在: {module_name}")


# =============================================================================
# 自我修复系统
# =============================================================================

@dataclass
class CodeIssue:
    """代码问题"""
    severity: str  # error, warning, info
    line: int
    column: int
    message: str
    code: str
    fix_suggestion: Optional[str] = None


class SelfRepair:
    """
    自我修复系统
    
    检测代码问题并提供修复建议
    """
    
    # 常见错误模式及修复建议
    ERROR_PATTERNS = {
        r'NameError:\s*name\s+[\'"](\w+)[\'"]\s+is\s+not\s+defined': {
            "type": "undefined_variable",
            "fix_template": "# 定义变量\n{{name}} = None  # TODO: 初始化变量"
        },
        r'AttributeError:\s*[\'"](\w+)[\'"]\s+object\s+has\s+no\s+attribute\s+[\'"](\w+)[\'"]': {
            "type": "missing_attribute",
            "fix_template": "# 添加缺失的属性\nself.{{attr}} = None  # 在__init__中添加"
        },
        r'ImportError:\s*No\s+module\s+named\s+[\'"]([\w.]+)[\'"]': {
            "type": "missing_import",
            "fix_template": "# 安装缺失的模块\n# pip install {{module}}"
        },
        r'SyntaxError:\s*invalid\s+syntax': {
            "type": "syntax_error",
            "fix_template": "# 检查语法错误\n# 常见原因: 括号不匹配、缩进错误、冒号缺失"
        },
        r'IndentationError:\s*': {
            "type": "indentation_error",
            "fix_template": "# 修复缩进\n# 确保使用一致的缩进（4个空格）"
        },
        r'TypeError:\s*(\w+)\(\)\s+takes\s+\d+\s+positional\s+argument': {
            "type": "wrong_arguments",
            "fix_template": "# 检查函数参数\n# 确保传递正确数量的参数"
        }
    }
    
    # 代码质量检查规则
    QUALITY_RULES = [
        {
            "name": "unused_import",
            "pattern": r'^import\s+(\w+)|^from\s+\S+\s+import\s+(\w+)',
            "message": "可能存在未使用的导入",
            "severity": "warning"
        },
        {
            "name": "bare_except",
            "pattern": r'except\s*:',
            "message": "使用裸except可能捕获过多异常",
            "severity": "warning"
        },
        {
            "name": "mutable_default",
            "pattern": r'def\s+\w+\s*\([^)]*=\s*(\[\s*\]|\{\s*\})',
            "message": "可变对象不应作为默认参数",
            "severity": "error"
        },
        {
            "name": "undefined_return",
            "pattern": r'def\s+\w+\s*\([^)]*\)(?!\s*->)',
            "message": "函数缺少返回类型注解",
            "severity": "info"
        }
    ]
    
    def __init__(self, code_generator: Optional[CodeGenerator] = None,
                 audit_logger: Optional[AuditLogger] = None):
        """
        初始化自我修复系统
        
        Args:
            code_generator: 代码生成器
            audit_logger: 审计日志记录器
        """
        self.code_generator = code_generator or CodeGenerator()
        self.audit_logger = audit_logger or AuditLogger()
        self.repair_history: List[Dict[str, Any]] = []
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        分析代码，检测问题
        
        Args:
            code: 要分析的代码
            
        Returns:
            Codong风格结果，包含问题列表
        """
        issues = []
        
        try:
            # 语法检查
            tree = ast.parse(code)
            
            # 代码质量检查
            quality_issues = self._check_quality(code)
            issues.extend(quality_issues)
            
            # AST分析
            ast_issues = self._analyze_ast(tree, code)
            issues.extend(ast_issues)
            
            return ok(issues)
        except SyntaxError as e:
            issues.append(CodeIssue(
                severity="error",
                line=e.lineno or 1,
                column=e.offset or 0,
                message=f"语法错误: {e.msg}",
                code="SYNTAX_ERROR",
                fix_suggestion="检查括号匹配、缩进和冒号"
            ))
            return ok(issues)
        except Exception as e:
            return err("ANALYZE_FAILED", f"分析失败: {str(e)}")
    
    def _check_quality(self, code: str) -> List[CodeIssue]:
        """检查代码质量"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            for rule in self.QUALITY_RULES:
                if re.search(rule["pattern"], line):
                    issues.append(CodeIssue(
                        severity=rule["severity"],
                        line=i,
                        column=0,
                        message=rule["message"],
                        code=rule["name"],
                        fix_suggestion=self._get_quality_fix(rule["name"])
                    ))
        
        return issues
    
    def _analyze_ast(self, tree: ast.AST, code: str) -> List[CodeIssue]:
        """使用AST分析代码"""
        issues = []
        
        for node in ast.walk(tree):
            # 检查空函数
            if isinstance(node, ast.FunctionDef):
                if not node.body or (len(node.body) == 1 and 
                                     isinstance(node.body[0], ast.Pass)):
                    issues.append(CodeIssue(
                        severity="warning",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"函数 '{node.name}' 为空",
                        code="EMPTY_FUNCTION",
                        fix_suggestion="实现函数逻辑或删除"
                    ))
            
            # 检查未使用的变量
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                # 简化检查，实际应该做更复杂的变量使用分析
                pass
        
        return issues
    
    def _get_quality_fix(self, rule_name: str) -> str:
        """获取质量问题的修复建议"""
        fixes = {
            "unused_import": "删除未使用的导入或使用该导入",
            "bare_except": "改为 'except Exception:' 或更具体的异常类型",
            "mutable_default": "使用 None 作为默认值，在函数内部初始化",
            "undefined_return": "添加返回类型注解，如 '-> Dict[str, Any]'"
        }
        return fixes.get(rule_name, "参考Python最佳实践")
    
    def diagnose_error(self, error: Exception, code: str) -> Dict[str, Any]:
        """
        诊断错误
        
        Args:
            error: 异常对象
            code: 相关代码
            
        Returns:
            Codong风格结果
        """
        error_str = str(error)
        error_type = type(error).__name__
        
        for pattern, info in self.ERROR_PATTERNS.items():
            match = re.search(pattern, error_str)
            if match:
                groups = match.groups()
                fix_template = info["fix_template"]
                
                # 填充修复模板
                fix_suggestion = fix_template
                for i, group in enumerate(groups):
                    fix_suggestion = fix_suggestion.replace(f"{{{'name' if i == 0 else 'attr' if i == 1 else 'module'}}}", group)
                
                return ok({
                    "error_type": info["type"],
                    "error_message": error_str,
                    "fix_suggestion": fix_suggestion,
                    "severity": "error"
                })
        
        # 未识别的错误
        return ok({
            "error_type": error_type,
            "error_message": error_str,
            "fix_suggestion": "请检查错误信息并手动修复",
            "severity": "error"
        })
    
    def generate_fix(self, code: str, issue: CodeIssue) -> Dict[str, Any]:
        """
        生成修复代码
        
        Args:
            code: 原始代码
            issue: 问题对象
            
        Returns:
            Codong风格结果
        """
        try:
            lines = code.split('\n')
            
            if issue.code == "SYNTAX_ERROR":
                # 语法错误需要手动修复
                return err("MANUAL_FIX_REQUIRED", "语法错误需要手动修复")
            
            elif issue.code == "EMPTY_FUNCTION":
                # 在空函数中添加TODO
                line_idx = issue.line - 1
                indent = len(lines[line_idx]) - len(lines[line_idx].lstrip())
                fix = " " * (indent + 4) + "# TODO: 实现函数逻辑"
                lines.insert(line_idx + 1, fix)
                return ok('\n'.join(lines))
            
            elif issue.code == "missing_import":
                # 添加导入语句
                fix_line = issue.fix_suggestion.split('\n')[0]
                lines.insert(0, fix_line)
                return ok('\n'.join(lines))
            
            elif issue.fix_suggestion:
                # 通用修复：添加注释
                line_idx = issue.line - 1
                indent = len(lines[line_idx]) - len(lines[line_idx].lstrip())
                fix = " " * indent + f"# FIXME: {issue.message}"
                lines.insert(line_idx, fix)
                return ok('\n'.join(lines))
            
            return err("NO_FIX_AVAILABLE", "没有可用的自动修复")
        except Exception as e:
            return err("GENERATE_FIX_FAILED", f"生成修复失败: {str(e)}")
    
    def apply_fix(self, file_path: str, original_code: str, 
                  fixed_code: str) -> Dict[str, Any]:
        """
        应用修复
        
        Args:
            file_path: 文件路径
            original_code: 原始代码
            fixed_code: 修复后的代码
            
        Returns:
            Codong风格结果
        """
        try:
            # 创建备份
            backup_result = self.audit_logger.create_backup(file_path)
            backup_path = None if is_error(backup_result) else unwrap(backup_result)
            
            # 写入修复后的代码
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            # 记录修复历史
            repair_record = {
                "timestamp": datetime.now().isoformat(),
                "file_path": file_path,
                "backup_path": backup_path,
                "original_hash": hashlib.md5(original_code.encode()).hexdigest(),
                "fixed_hash": hashlib.md5(fixed_code.encode()).hexdigest()
            }
            self.repair_history.append(repair_record)
            
            # 记录审计日志
            self.audit_logger.log(
                operation="APPLY_FIX",
                file_path=file_path,
                backup_path=backup_path,
                details=repair_record,
                success=True
            )
            
            return ok({
                "file_path": file_path,
                "backup_path": backup_path
            })
        except Exception as e:
            return err("APPLY_FIX_FAILED", f"应用修复失败: {str(e)}")
    
    def auto_repair(self, file_path: str) -> Dict[str, Any]:
        """
        自动修复文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Codong风格结果
        """
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 分析代码
            analysis = self.analyze_code(code)
            if is_error(analysis):
                return analysis
            
            issues = unwrap(analysis)
            
            if not issues:
                return ok({"message": "没有发现需要修复的问题", "fixes_applied": 0})
            
            # 按严重性排序
            severity_order = {"error": 0, "warning": 1, "info": 2}
            issues.sort(key=lambda x: severity_order.get(x.severity, 3))
            
            fixed_code = code
            fixes_applied = 0
            
            # 应用修复
            for issue in issues:
                if issue.severity == "error":
                    fix_result = self.generate_fix(fixed_code, issue)
                    if not is_error(fix_result):
                        fixed_code = unwrap(fix_result)
                        fixes_applied += 1
            
            # 如果代码有变化，应用修复
            if fixed_code != code:
                apply_result = self.apply_fix(file_path, code, fixed_code)
                if is_error(apply_result):
                    return apply_result
            
            return ok({
                "file_path": file_path,
                "issues_found": len(issues),
                "fixes_applied": fixes_applied,
                "issues": [{"line": i.line, "message": i.message, "severity": i.severity} for i in issues]
            })
        except Exception as e:
            return err("AUTO_REPAIR_FAILED", f"自动修复失败: {str(e)}")


# =============================================================================
# 热加载系统
# =============================================================================

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    file_path: str
    last_modified: float
    hash: str
    module: types.ModuleType


class HotLoader:
    """
    热加载器
    
    支持运行时模块热更新
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        初始化热加载器
        
        Args:
            audit_logger: 审计日志记录器
        """
        self.audit_logger = audit_logger or AuditLogger()
        self.watched_modules: Dict[str, ModuleInfo] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.watching = False
        self.watch_thread: Optional[threading.Thread] = None
        self.watch_interval = 1.0  # 检查间隔（秒）
        self.lock = threading.RLock()
    
    def watch(self, module_name: str, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        监视模块
        
        Args:
            module_name: 模块名称
            callback: 模块更新时的回调函数
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            try:
                # 获取模块
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                
                # 获取模块文件路径
                if not hasattr(module, '__file__') or not module.__file__:
                    return err("NOT_FILE_MODULE", "无法监视非文件模块")
                
                file_path = module.__file__
                
                # 计算文件哈希
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                # 记录模块信息
                self.watched_modules[module_name] = ModuleInfo(
                    name=module_name,
                    file_path=file_path,
                    last_modified=os.path.getmtime(file_path),
                    hash=file_hash,
                    module=module
                )
                
                # 注册回调
                if callback:
                    if module_name not in self.callbacks:
                        self.callbacks[module_name] = []
                    self.callbacks[module_name].append(callback)
                
                # 记录审计日志
                self.audit_logger.log(
                    operation="WATCH_MODULE",
                    file_path=file_path,
                    details={"module_name": module_name},
                    success=True
                )
                
                return ok({
                    "module_name": module_name,
                    "file_path": file_path
                })
            except Exception as e:
                return err("WATCH_FAILED", f"监视模块失败: {str(e)}")
    
    def unwatch(self, module_name: str) -> Dict[str, Any]:
        """
        取消监视模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            if module_name in self.watched_modules:
                info = self.watched_modules.pop(module_name)
                self.callbacks.pop(module_name, None)
                
                self.audit_logger.log(
                    operation="UNWATCH_MODULE",
                    file_path=info.file_path,
                    details={"module_name": module_name},
                    success=True
                )
                return ok(True)
            return err("NOT_WATCHED", f"模块未被监视: {module_name}")
    
    def check_updates(self) -> Dict[str, Any]:
        """
        检查模块更新
        
        Returns:
            Codong风格结果，包含更新的模块列表
        """
        with self.lock:
            updated = []
            
            for module_name, info in self.watched_modules.items():
                try:
                    # 检查文件修改时间
                    current_mtime = os.path.getmtime(info.file_path)
                    if current_mtime <= info.last_modified:
                        continue
                    
                    # 计算新哈希
                    with open(info.file_path, 'rb') as f:
                        current_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if current_hash != info.hash:
                        updated.append({
                            "module_name": module_name,
                            "file_path": info.file_path,
                            "old_hash": info.hash,
                            "new_hash": current_hash
                        })
                except Exception:
                    pass
            
            return ok(updated)
    
    def reload(self, module_name: str) -> Dict[str, Any]:
        """
        重新加载模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            try:
                if module_name not in self.watched_modules:
                    return err("NOT_WATCHED", f"模块未被监视: {module_name}")
                
                info = self.watched_modules[module_name]
                
                # 创建备份
                backup_result = self.audit_logger.create_backup(info.file_path)
                backup_path = None if is_error(backup_result) else unwrap(backup_result)
                
                # 重新加载模块
                new_module = importlib.reload(info.module)
                
                # 更新模块信息
                with open(info.file_path, 'rb') as f:
                    new_hash = hashlib.md5(f.read()).hexdigest()
                
                self.watched_modules[module_name] = ModuleInfo(
                    name=module_name,
                    file_path=info.file_path,
                    last_modified=os.path.getmtime(info.file_path),
                    hash=new_hash,
                    module=new_module
                )
                
                # 记录审计日志
                self.audit_logger.log(
                    operation="RELOAD_MODULE",
                    file_path=info.file_path,
                    backup_path=backup_path,
                    details={
                        "module_name": module_name,
                        "old_hash": info.hash,
                        "new_hash": new_hash
                    },
                    success=True
                )
                
                # 执行回调
                if module_name in self.callbacks:
                    for callback in self.callbacks[module_name]:
                        try:
                            callback(new_module)
                        except Exception as e:
                            print(f"回调执行失败: {e}")
                
                return ok({
                    "module_name": module_name,
                    "module": new_module
                })
            except Exception as e:
                return err("RELOAD_FAILED", f"重新加载模块失败: {str(e)}")
    
    def start_watching(self, interval: Optional[float] = None) -> Dict[str, Any]:
        """
        启动监视线程
        
        Args:
            interval: 检查间隔（秒）
            
        Returns:
            Codong风格结果
        """
        with self.lock:
            if self.watching:
                return err("ALREADY_WATCHING", "监视已在运行")
            
            if interval:
                self.watch_interval = interval
            
            self.watching = True
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()
            
            return ok(True)
    
    def stop_watching(self) -> Dict[str, Any]:
        """
        停止监视线程
        
        Returns:
            Codong风格结果
        """
        with self.lock:
            if not self.watching:
                return err("NOT_WATCHING", "监视未在运行")
            
            self.watching = False
            if self.watch_thread:
                self.watch_thread.join(timeout=2.0)
            
            return ok(True)
    
    def _watch_loop(self) -> None:
        """监视循环"""
        while self.watching:
            try:
                updates = unwrap(self.check_updates())
                for update in updates:
                    module_name = update["module_name"]
                    print(f"检测到模块更新: {module_name}")
                    self.reload(module_name)
            except Exception as e:
                print(f"监视循环出错: {e}")
            
            time.sleep(self.watch_interval)
    
    def get_watched_modules(self) -> Dict[str, Any]:
        """获取所有被监视的模块"""
        with self.lock:
            return ok({
                name: {
                    "file_path": info.file_path,
                    "last_modified": info.last_modified,
                    "hash": info.hash
                }
                for name, info in self.watched_modules.items()
            })


# =============================================================================
# 全局自编译函数
# =============================================================================

class SelfCompilingModule:
    """
    自编译模块主类
    
    整合所有功能，提供统一的自编译接口
    """
    
    _instance: Optional['SelfCompilingModule'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化自编译模块
        
        Args:
            log_dir: 日志目录
        """
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # 初始化组件
        self.audit_logger = AuditLogger(log_dir)
        self.code_generator = CodeGenerator(self.audit_logger)
        self.self_repair = SelfRepair(self.code_generator, self.audit_logger)
        self.hot_loader = HotLoader(self.audit_logger)
        
        # 注册内置模板
        self._register_builtin_templates()
    
    def _register_builtin_templates(self) -> None:
        """注册内置模板"""
        # 已经在CodeGenerator初始化时加载
        pass
    
    def compile_template(self, template_name: str, **kwargs) -> Dict[str, Any]:
        """
        编译模板
        
        Args:
            template_name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            Codong风格结果
        """
        try:
            if template_name not in self.code_generator.templates:
                return err("TEMPLATE_NOT_FOUND", f"模板不存在: {template_name}")
            
            template = self.code_generator.templates[template_name]
            code = unwrap(template.render(**kwargs))
            
            return ok(code)
        except Exception as e:
            return err("COMPILE_TEMPLATE_FAILED", f"编译模板失败: {str(e)}")
    
    def generate_and_load(self, template_name: str, module_name: str,
                         **kwargs) -> Dict[str, Any]:
        """
        生成代码并加载为模块
        
        Args:
            template_name: 模板名称
            module_name: 模块名称
            **kwargs: 模板变量
            
        Returns:
            Codong风格结果
        """
        try:
            # 编译模板
            code_result = self.compile_template(template_name, **kwargs)
            if is_error(code_result):
                return code_result
            
            code = unwrap(code_result)
            
            # 创建模块
            module = unwrap(self.code_generator.create_module(code, module_name))
            
            # 保存源代码
            module.__source__ = code
            
            return ok(module)
        except Exception as e:
            return err("GENERATE_AND_LOAD_FAILED", f"生成并加载失败: {str(e)}")
    
    def self_compile(self, source_code: str, module_name: str,
                     auto_repair: bool = True) -> Dict[str, Any]:
        """
        自编译代码
        
        完整的自编译流程：分析 -> 修复 -> 编译 -> 加载
        
        Args:
            source_code: 源代码
            module_name: 模块名称
            auto_repair: 是否自动修复
            
        Returns:
            Codong风格结果
        """
        try:
            code = source_code
            
            # 1. 分析代码
            analysis = self.self_repair.analyze_code(code)
            if is_error(analysis):
                return analysis
            
            issues = unwrap(analysis)
            
            # 2. 自动修复
            if auto_repair and issues:
                # 应用简单修复
                for issue in issues:
                    if issue.severity == "error":
                        fix_result = self.self_repair.generate_fix(code, issue)
                        if not is_error(fix_result):
                            code = unwrap(fix_result)
            
            # 3. 编译代码
            compile_result = self.code_generator.compile_code(code, module_name)
            if is_error(compile_result):
                return compile_result
            
            compiled = unwrap(compile_result)
            
            # 4. 创建模块
            module = unwrap(self.code_generator.create_module(code, module_name))
            module.__compiled__ = compiled
            module.__source__ = code
            
            return ok({
                "module": module,
                "module_name": module_name,
                "issues_detected": len(issues),
                "code_compiled": True
            })
        except Exception as e:
            return err("SELF_COMPILE_FAILED", f"自编译失败: {str(e)}")
    
    def enable_hot_reload(self, module_name: str, 
                         callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        启用热重载
        
        Args:
            module_name: 模块名称
            callback: 更新回调
            
        Returns:
            Codong风格结果
        """
        return self.hot_loader.watch(module_name, callback)
    
    def start_auto_reload(self, interval: float = 1.0) -> Dict[str, Any]:
        """
        启动自动重载
        
        Args:
            interval: 检查间隔（秒）
            
        Returns:
            Codong风格结果
        """
        return self.hot_loader.start_watching(interval)
    
    def stop_auto_reload(self) -> Dict[str, Any]:
        """停止自动重载"""
        return self.hot_loader.stop_watching()
    
    def get_audit_history(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取审计历史
        
        Args:
            file_path: 筛选特定文件
            
        Returns:
            Codong风格结果
        """
        return self.audit_logger.get_history(file_path)
    
    def rollback(self, entry_index: int = -1) -> Dict[str, Any]:
        """
        回滚操作
        
        Args:
            entry_index: 日志条目索引
            
        Returns:
            Codong风格结果
        """
        return self.audit_logger.rollback(entry_index)


# =============================================================================
# 便捷函数
# =============================================================================

def get_self_compiler(log_dir: Optional[str] = None) -> SelfCompilingModule:
    """
    获取自编译模块实例
    
    Args:
        log_dir: 日志目录
        
    Returns:
        SelfCompilingModule实例
    """
    return SelfCompilingModule(log_dir)


def compile_template(template_name: str, **kwargs) -> Dict[str, Any]:
    """
    编译模板（便捷函数）
    
    Args:
        template_name: 模板名称
        **kwargs: 模板变量
        
    Returns:
        Codong风格结果
    """
    compiler = get_self_compiler()
    return compiler.compile_template(template_name, **kwargs)


def self_compile(source_code: str, module_name: str,
                auto_repair: bool = True) -> Dict[str, Any]:
    """
    自编译代码（便捷函数）
    
    Args:
        source_code: 源代码
        module_name: 模块名称
        auto_repair: 是否自动修复
        
    Returns:
        Codong风格结果
    """
    compiler = get_self_compiler()
    return compiler.self_compile(source_code, module_name, auto_repair)


def generate_function(name: str, params: List[Dict[str, Any]], 
                     body: str, description: str = "") -> Dict[str, Any]:
    """
    生成函数代码（便捷函数）
    
    Args:
        name: 函数名
        params: 参数列表
        body: 函数体
        description: 描述
        
    Returns:
        Codong风格结果
    """
    generator = CodeGenerator()
    return generator.generate_function(name, params, body, description)


def enable_hot_reload(module_name: str, 
                     callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    启用热重载（便捷函数）
    
    Args:
        module_name: 模块名称
        callback: 更新回调
        
    Returns:
        Codong风格结果
    """
    compiler = get_self_compiler()
    return compiler.enable_hot_reload(module_name, callback)


def analyze_code(code: str) -> Dict[str, Any]:
    """
    分析代码（便捷函数）
    
    Args:
        code: 代码字符串
        
    Returns:
        Codong风格结果
    """
    repair = SelfRepair()
    return repair.analyze_code(code)


def auto_repair(file_path: str) -> Dict[str, Any]:
    """
    自动修复文件（便捷函数）
    
    Args:
        file_path: 文件路径
        
    Returns:
        Codong风格结果
    """
    repair = SelfRepair()
    return repair.auto_repair(file_path)


# =============================================================================
# 示例用法
# =============================================================================

if __name__ == "__main__":
    # 示例1: 使用模板生成代码
    print("=" * 50)
    print("示例1: 使用模板生成代码")
    print("=" * 50)
    
    template = CodeTemplate("function")
    template.define_variable("name", "str", required=True, description="函数名")
    template.define_variable("params", "str", default="", description="参数")
    template.define_variable("body", "code", required=True, description="函数体")
    template.define_variable("description", "str", default="", description="描述")
    
    result = template.render(
        name="greet",
        params="name: str",
        body='return f"Hello, {name}!"',
        description="问候函数"
    )
    
    if not is_error(result):
        print(unwrap(result))
    
    # 示例2: 代码生成器
    print("\n" + "=" * 50)
    print("示例2: 代码生成器")
    print("=" * 50)
    
    generator = CodeGenerator()
    
    # 生成函数
    func_result = generator.generate_function(
        name="calculate_sum",
        params=[
            {"name": "a", "type": "int"},
            {"name": "b", "type": "int", "default": 0}
        ],
        body="result = a + b\nreturn result",
        description="计算两个数的和",
        return_type="int"
    )
    
    if not is_error(func_result):
        print(unwrap(func_result))
    
    # 示例3: 代码分析
    print("\n" + "=" * 50)
    print("示例3: 代码分析")
    print("=" * 50)
    
    sample_code = '''
def empty_function():
    pass

def bad_function(x=[]):
    return x
'''
    
    analysis = analyze_code(sample_code)
    if not is_error(analysis):
        issues = unwrap(analysis)
        for issue in issues:
            print(f"行{issue.line}: [{issue.severity}] {issue.message}")
    
    # 示例4: 自编译
    print("\n" + "=" * 50)
    print("示例4: 自编译")
    print("=" * 50)
    
    source = '''
def hello(name: str = "World") -> str:
    """问候函数"""
    return f"Hello, {name}!"

class Greeter:
    """问候器"""
    def __init__(self):
        self.name = "Greeter"
    
    def greet(self, name: str) -> str:
        return f"{self.name} says: Hello, {name}!"
'''
    
    compile_result = self_compile(source, "example_module")
    if not is_error(compile_result):
        result = unwrap(compile_result)
        module = result["module"]
        print(f"模块编译成功: {result['module_name']}")
        print(f"检测到问题数: {result['issues_detected']}")
        print(f"调用 hello(): {module.hello('Python')}")
        
        greeter = module.Greeter()
        print(f"调用 Greeter.greet(): {greeter.greet('Self-Compiling')}")
    
    print("\n" + "=" * 50)
    print("所有示例执行完成!")
    print("=" * 50)
