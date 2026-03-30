"""
Temper Tools - Self 模块（自我进化）

提供自我记录、自我分析、自我快照的能力
"""

import os
import json
import hashlib
from datetime import datetime
from difflib import unified_diff
from ..core.errors import error, ok

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = os.path.join(SCRIPT_DIR, ".temper_backups")
JOURNAL_DIR = os.path.join(SCRIPT_DIR, "journal")
SNAPSHOT_INDEX = os.path.join(BACKUP_DIR, "snapshot_index.json")


def _ensure_dirs():
    """确保必要目录存在"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(JOURNAL_DIR, exist_ok=True)


def _load_snapshot_index():
    """加载快照索引"""
    _ensure_dirs()
    if os.path.exists(SNAPSHOT_INDEX):
        try:
            with open(SNAPSHOT_INDEX, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"snapshots": []}
    return {"snapshots": []}


def _save_snapshot_index(index):
    """保存快照索引"""
    with open(SNAPSHOT_INDEX, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _get_file_hash(filepath):
    """计算文件 MD5 哈希"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()[:8]


def snapshot(files=None, tag=""):
    """
    创建代码快照

    在执行修改前保存当前代码状态，用于后续对比。

    Args:
        files: 要快照的文件列表，默认为 ["temper.py"]
        tag: 快照标签，用于标识此次快照的目的

    Returns:
        成功: {"ok": True, "value": {"snapshot_id": "...", "files": [...]}}
    """
    _ensure_dirs()

    if files is None:
        files = ["temper.py"]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_id = f"snap_{timestamp}"
    snapshot_dir = os.path.join(BACKUP_DIR, snapshot_id)

    os.makedirs(snapshot_dir, exist_ok=True)

    snapshot_files = []

    for file in files:
        src_path = os.path.join(SCRIPT_DIR, file)
        if os.path.exists(src_path):
            dst_path = os.path.join(snapshot_dir, os.path.basename(file))
            with open(src_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(dst_path, 'w', encoding='utf-8') as f:
                f.write(content)

            snapshot_files.append({
                "file": file,
                "hash": _get_file_hash(src_path),
                "lines": len(content.split('\n'))
            })

    index = _load_snapshot_index()
    index["snapshots"].append({
        "id": snapshot_id,
        "timestamp": timestamp,
        "tag": tag,
        "files": snapshot_files
    })
    _save_snapshot_index(index)

    return ok({
        "snapshot_id": snapshot_id,
        "path": snapshot_dir,
        "files": snapshot_files,
        "tag": tag
    })


def diff(snapshot_id=None):
    """
    对比当前代码与快照

    显示代码变更，用于分析自我进化的具体内容。

    Args:
        snapshot_id: 快照 ID，默认使用最新的快照

    Returns:
        成功: {"ok": True, "value": {"changes": [...], "summary": "..."}}
    """
    _ensure_dirs()

    index = _load_snapshot_index()

    if not index["snapshots"]:
        return error(
            "E6001_NO_SNAPSHOT",
            "没有可用的快照",
            fix="先使用 self.snapshot 创建快照",
            retryable=False
        )

    if snapshot_id is None:
        snapshot_data = index["snapshots"][-1]
    else:
        snapshot_data = next((s for s in index["snapshots"] if s["id"] == snapshot_id), None)
        if snapshot_data is None:
            return error(
                "E6002_SNAPSHOT_NOT_FOUND",
                f"快照不存在: {snapshot_id}",
                fix="使用 self.list_snapshots 查看可用快照",
                retryable=False
            )

    snapshot_id = snapshot_data["id"]
    snapshot_dir = os.path.join(BACKUP_DIR, snapshot_id)

    changes = []
    total_additions = 0
    total_deletions = 0

    for file_info in snapshot_data["files"]:
        file = file_info["file"]
        current_path = os.path.join(SCRIPT_DIR, file)
        snapshot_path = os.path.join(snapshot_dir, os.path.basename(file))

        if not os.path.exists(current_path):
            changes.append({"file": file, "status": "deleted", "diff": "文件已删除"})
            continue

        if not os.path.exists(snapshot_path):
            changes.append({"file": file, "status": "new", "diff": "新文件"})
            continue

        with open(current_path, 'r', encoding='utf-8') as f:
            current_lines = f.readlines()
        with open(snapshot_path, 'r', encoding='utf-8') as f:
            snapshot_lines = f.readlines()

        diff_lines = list(unified_diff(
            snapshot_lines,
            current_lines,
            fromfile=f"{file} (快照)",
            tofile=f"{file} (当前)",
            lineterm=''
        ))

        if diff_lines:
            additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
            deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

            total_additions += additions
            total_deletions += deletions

            changes.append({
                "file": file,
                "status": "modified",
                "additions": additions,
                "deletions": deletions,
                "diff": ''.join(diff_lines[:100])
            })

    summary = f"共 {len(changes)} 个文件变更，+{total_additions}/-{total_deletions} 行"

    return ok({
        "snapshot_id": snapshot_id,
        "changes": changes,
        "summary": summary,
        "total_additions": total_additions,
        "total_deletions": total_deletions
    })


def log(title="", description=""):
    """
    自动生成进化日志

    基于最新的 diff 结果，生成 journal/day-XXX.md 格式的日志。

    Args:
        title: 日志标题
        description: 日志描述

    Returns:
        成功: {"ok": True, "value": {"path": "...", "content": "..."}}
    """
    _ensure_dirs()

    existing_logs = [f for f in os.listdir(JOURNAL_DIR) if f.startswith('day-') and f.endswith('.md')]
    day_num = len(existing_logs) + 1
    log_filename = f"day-{day_num:03d}.md"
    log_path = os.path.join(JOURNAL_DIR, log_filename)

    diff_result = diff()

    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""# Day {day_num}: {title or '进化记录'}

**日期**: {today}
**主题**: {title or '自我进化'}
**状态**: ✅ 完成

---

## 今日目标

{description or '完成新的自我进化能力。'}

---

## 变更记录

"""

    if diff_result["ok"]:
        changes = diff_result["value"]["changes"]

        content += f"""### 代码变更概览

{diff_result["value"]["summary"]}

| 文件 | 状态 | 新增 | 删除 |
|------|------|------|------|
"""

        for change in changes:
            status = change["status"]
            additions = change.get("additions", "-")
            deletions = change.get("deletions", "-")
            content += f"| {change['file']} | {status} | {additions} | {deletions} |\n"

        content += "\n---\n\n## 详细变更\n\n"

        for change in changes:
            if change["status"] == "modified":
                content += f"### {change['file']}\n\n```\n{change['diff'][:500]}...\n```\n\n"

    else:
        content += f"无法获取变更详情: {diff_result.get('error', '未知错误')}\n\n"

    content += """---

## Next 目标

待定...

---

*自我修改，自我进化。*
"""

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return ok({
        "path": log_path,
        "filename": log_filename,
        "day": day_num,
        "content": content
    })


def list_snapshots():
    """
    列出所有快照

    Returns:
        成功: {"ok": True, "value": {"snapshots": [...], "count": N}}
    """
    index = _load_snapshot_index()

    return ok({
        "snapshots": index["snapshots"],
        "count": len(index["snapshots"])
    })
