"""
Temper 安全编辑模块 - 测试驱动 + 自动回滚
学习 yoyo-evolve 的自我验证思想
"""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from ..core.errors import error, ok

# 备份目录
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".temper_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def create_backup(path):
    """创建文件备份"""
    try:
        if not os.path.exists(path):
            return error("E1001_FILE_NOT_FOUND", f"无法备份：文件不存在 {path}")

        # 生成备份文件名: timestamp_originalname
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.basename(path)
        backup_name = f"{timestamp}_{filename}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)

        # 复制文件
        shutil.copy2(path, backup_path)

        return ok({
            "backup_path": backup_path,
            "original_path": path,
            "timestamp": timestamp
        })
    except Exception as e:
        return error("E6001_BACKUP_FAILED", f"备份失败: {str(e)}", fix="检查磁盘空间和权限")

def restore_backup(backup_info):
    """从备份恢复文件"""
    try:
        backup_path = backup_info.get("backup_path")
        original_path = backup_info.get("original_path")

        if not os.path.exists(backup_path):
            return error("E6002_BACKUP_NOT_FOUND", f"备份文件不存在: {backup_path}")

        shutil.copy2(backup_path, original_path)
        return ok(f"已恢复到: {original_path}")
    except Exception as e:
        return error("E6003_RESTORE_FAILED", f"恢复失败: {str(e)}")

def run_syntax_check(path):
    """运行 Python 语法检查"""
    if not path.endswith('.py'):
        return ok("非 Python 文件，跳过语法检查")

    try:
        # 使用 py_compile 验证语法
        result = subprocess.run(
            ['python', '-m', 'py_compile', path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return ok("语法检查通过")
        else:
            return error(
                "E6004_SYNTAX_ERROR",
                f"语法错误: {result.stderr}",
                fix="检查 Python 语法",
                retryable=False
            )
    except Exception as e:
        return error("E6005_CHECK_FAILED", f"语法检查失败: {str(e)}")

def run_tests(test_path=None):
    """运行测试（如果存在）"""
    # 查找测试文件
    if test_path is None:
        # 默认查找 test_*.py 或 *_test.py
        base_dir = os.getcwd()
        test_files = []
        for pattern in ['test_*.py', '*_test.py', 'tests/*.py']:
            import glob
            test_files.extend(glob.glob(os.path.join(base_dir, pattern)))

        if not test_files:
            return ok("未找到测试文件，跳过测试")

        test_path = test_files[0]

    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', test_path, '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # 解析测试结果
            lines = result.stdout.split('\n')
            passed = sum(1 for line in lines if 'PASSED' in line)
            failed = sum(1 for line in lines if 'FAILED' in line)

            return ok({
                "message": f"测试通过: {passed} passed",
                "passed": passed,
                "failed": 0,
                "details": result.stdout[-500:]  # 最后 500 字符
            })
        else:
            return error(
                "E6006_TEST_FAILED",
                f"测试失败: {result.stderr[:200]}",
                fix="修复代码中的错误",
                retryable=False
            )
    except FileNotFoundError:
        # pytest 未安装，尝试用 unittest
        return ok("pytest 未安装，跳过详细测试")
    except Exception as e:
        return error("E6007_TEST_ERROR", f"测试运行失败: {str(e)}")

def safe_edit(path, old_string, new_string, verify=True):
    """
    安全编辑文件 - 带备份和自动回滚

    Args:
        path: 文件路径
        old_string: 原内容
        new_string: 新内容
        verify: 是否验证（语法检查+测试）

    Returns:
        {"ok": True, "value": "成功修改...", "backup": {...}}
        {"ok": False, "error": "...", "restored": True}
    """
    from ..tools.fs import read, edit

    # 1. 创建备份
    backup = create_backup(path)
    if not backup.get("ok"):
        return backup

    backup_info = backup.get("value", {})

    # 2. 执行编辑
    edit_result = edit(path, old_string, new_string)
    if not edit_result.get("ok"):
        return edit_result

    # 3. 验证（如果启用）
    if verify:
        # 3.1 语法检查
        syntax = run_syntax_check(path)
        if not syntax.get("ok"):
            # 语法错误，回滚
            restore_backup(backup_info)
            return error(
                "E6008_EDIT_ROLLED_BACK",
                f"修改导致语法错误，已自动回滚。错误: {syntax.get('message')}",
                fix="修正 new_string 的语法错误",
                retryable=True,
                extra={"original_error": syntax, "restored": True}
            )

        # 3.2 运行测试
        test = run_tests()
        if not test.get("ok"):
            # 测试失败，回滚
            restore_backup(backup_info)
            return error(
                "E6009_EDIT_ROLLED_BACK",
                f"修改导致测试失败，已自动回滚。错误: {test.get('message')}",
                fix="检查修改逻辑是否正确",
                retryable=True,
                extra={"original_error": test, "restored": True}
            )

    # 4. 成功 - 保留修改，返回备份信息
    return ok({
        "message": f"成功修改 {path}（已备份）",
        "backup_info": backup_info,
        "verified": verify
    })

def get_backup_list():
    """获取备份列表"""
    try:
        backups = []
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.py'):
                # 解析时间戳
                parts = f.split('_', 2)
                if len(parts) >= 3:
                    timestamp = f"{parts[0]}_{parts[1]}"
                    original = parts[2]
                    backups.append({
                        "file": f,
                        "timestamp": timestamp,
                        "original": original,
                        "path": os.path.join(BACKUP_DIR, f)
                    })

        # 按时间排序
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return ok(backups)
    except Exception as e:
        return error("E6010_LIST_BACKUP_FAILED", f"获取备份列表失败: {str(e)}")

def cleanup_old_backups(keep=10):
    """清理旧备份，只保留最近 N 个"""
    result = get_backup_list()
    if not result.get("ok"):
        return result

    backups = result.get("value", [])
    if len(backups) <= keep:
        return ok(f"无需清理，当前 {len(backups)} 个备份")

    # 删除旧备份
    removed = 0
    for backup in backups[keep:]:
        try:
            os.remove(backup["path"])
            removed += 1
        except:
            pass

    return ok(f"已清理 {removed} 个旧备份，保留最近 {keep} 个")
