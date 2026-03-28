"""
Temper Tools - Self 模块（自我修改）
带测试验证和自动回滚
"""

from ..core.safe_edit import safe_edit, get_backup_list, restore_backup, cleanup_old_backups

def edit_safe(path, old_string, new_string, verify=True):
    """
    安全编辑 - 带备份、验证、自动回滚

    Args:
        path: 文件路径
        old_string: 原内容
        new_string: 新内容
        verify: 是否验证（默认 True）

    Returns:
        成功: {"ok": True, "value": {"message": "...", "backup_info": {...}}}
        失败: {"ok": False, "error": "...", "message": "..."}
    """
    return safe_edit(path, old_string, new_string, verify=verify)

def list_backups():
    """列出所有备份"""
    return get_backup_list()

def restore(path, timestamp=None):
    """
    恢复到指定备份
    Args:
        path: 原文件路径（用于查找对应备份）
        timestamp: 备份时间戳（可选，默认恢复最新）
    """
    from ..core.errors import error, ok
    import os

    # 获取备份列表
    result = get_backup_list()
    if not result.get("ok"):
        return result

    backups = result.get("value", [])
    if not backups:
        return error("E6002_NO_BACKUP", "没有找到备份")

    filename = os.path.basename(path)

    # 过滤出该文件的备份
    file_backups = [b for b in backups if b["original"] == filename]
    if not file_backups:
        return error("E6002_NO_BACKUP", f"没有找到 {filename} 的备份")

    # 选择备份
    if timestamp:
        backup = next((b for b in file_backups if b["timestamp"] == timestamp), None)
        if not backup:
            return error("E6003_BACKUP_NOT_FOUND", f"没有找到时间戳 {timestamp} 的备份")
    else:
        backup = file_backups[0]  # 最新的

    # 恢复
    return restore_backup({
        "backup_path": backup["path"],
        "original_path": path
    })

def cleanup(keep=10):
    """清理旧备份"""
    return cleanup_old_backups(keep=keep)
