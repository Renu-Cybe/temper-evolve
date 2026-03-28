"""
Temper Tools - FS 模块（文件系统）
学习 Codong 的 fs 风格，统一文件操作
"""

import os
import json
from ..core.errors import error, ok
from ..core.types import validate_path, validate_string

# 脚本所在目录，用于相对路径解析
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _resolve_path(path):
    """解析路径（支持相对路径）"""
    if not os.path.isabs(path):
        return os.path.join(SCRIPT_DIR, path)
    return path

def read(path, offset=0, limit=None):
    """
    读取文件内容

    Args:
        path: 文件路径（支持相对路径）
        offset: 起始行号（从0开始，可选）
        limit: 读取行数（可选，None表示读取全部）

    Returns:
        成功: {"ok": True, "value": "文件内容"}
        失败: {"ok": False, "error": "E1001_FILE_NOT_FOUND", ...}
    """
    # 验证参数
    validated = validate_path(path)
    if not validated["ok"]:
        return validated

    path = _resolve_path(validated["value"])

    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 处理 offset
        if offset < 0:
            offset = 0
        if offset >= total_lines:
            return ok("")
        
        # 处理 limit
        end_line = total_lines
        if limit is not None and limit > 0:
            end_line = min(offset + limit, total_lines)
        
        # 提取指定范围的行
        selected_lines = lines[offset:end_line]
        content = ''.join(selected_lines)
        
        # 添加文件信息
        info = f"[文件: {path}, 总行数: {total_lines}, 显示: {offset+1}-{end_line}行]\n"
        
        return ok(info + content)
    except FileNotFoundError:
        return error(
            "E1001_FILE_NOT_FOUND",
            f"文件不存在: {path}",
            fix=f"检查路径是否正确，或使用 fs.exists('{path}') 验证",
            retryable=False
        )
    except PermissionError:
        return error(
            "E1003_PERMISSION_DENIED",
            f"没有权限读取: {path}",
            fix="检查文件权限或以管理员身份运行",
            retryable=False
        )
    except Exception as e:
        return error(
            "E1000_FILE_ERROR",
            f"读取失败: {str(e)}",
            fix="检查文件是否被占用",
            retryable=True
        )

def write(path, content):
    """写入文件（创建或覆盖）"""
    validated_path = validate_path(path)
    if not validated_path["ok"]:
        return validated_path

    validated_content = validate_string(content)
    if not validated_content["ok"]:
        return validated_content

    path = _resolve_path(validated_path["value"])
    content = validated_content["value"]

    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return ok(f"已写入 {path}")
    except Exception as e:
        return error(
            "E1000_FILE_ERROR",
            f"写入失败: {str(e)}",
            fix="检查磁盘空间和权限",
            retryable=False
        )

def edit(path, old_string, new_string):
    """
    编辑文件内容（精确匹配替换）

    Args:
        path: 文件路径
        old_string: 要替换的原内容（必须精确匹配）
        new_string: 新内容

    Returns:
        成功: {"ok": True, "value": "成功修改 ..."}
        失败: {"ok": False, "error": "E2001_EDIT_NO_MATCH", ...}
    """
    # 读取文件
    result = read(path)
    if not result["ok"]:
        return result

    content = result.get("value", "")

    # 验证 old_string
    validated = validate_string(old_string, "old_string")
    if not validated["ok"]:
        return validated
    old_string = validated["value"]

    if old_string not in content:
        return error(
            "E2001_EDIT_NO_MATCH",
            f"在文件 {path} 中未找到匹配内容",
            fix="确保 old_string 是从文件中复制的精确内容",
            retryable=False
        )

    # 执行替换
    new_content = content.replace(old_string, new_string, 1)

    # Python 语法检查（如果是 .py 文件）
    if path.endswith('.py'):
        import ast
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return error(
                "E2002_SYNTAX_ERROR",
                f"修改会导致 Python 语法错误: {e}",
                fix="检查替换内容的语法",
                retryable=False
            )

    # 写回文件
    write_result = write(path, new_content)
    if write_result["ok"]:
        return ok(f"成功修改 {path}")
    return write_result

def exists(path):
    """检查路径是否存在"""
    validated = validate_path(path)
    if not validated["ok"]:
        return validated

    path = _resolve_path(validated["value"])
    return ok(os.path.exists(path))

def list_dir(path="."):
    """列出目录内容"""
    validated = validate_path(path)
    if not validated["ok"]:
        return validated

    path = _resolve_path(validated["value"])

    try:
        items = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            items.append({
                "name": name,
                "path": full_path,
                "is_dir": os.path.isdir(full_path),
                "size": os.path.getsize(full_path) if os.path.isfile(full_path) else 0
            })
        return ok(items)
    except Exception as e:
        return error(
            "E1000_FILE_ERROR",
            f"无法列出目录: {str(e)}",
            fix="检查路径是否存在且有权限访问",
            retryable=False
        )

def read_json(path):
    """读取并解析 JSON 文件"""
    result = read(path)
    if not result["ok"]:
        return result

    try:
        data = json.loads(result["value"])
        return ok(data)
    except json.JSONDecodeError as e:
        return error(
            "E3002_JSON_INVALID",
            f"JSON 解析失败: {str(e)}",
            fix="检查文件内容是否为有效的 JSON",
            retryable=False
        )
