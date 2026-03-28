#!/usr/bin/env python3
"""
🧊 Temper Evolve v2.0 - Codong 风格重构版

AI 原生 Coding Agent，结构化错误处理，模块化工具系统
"""

import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from openai import OpenAI

from temper.core.errors import is_error, is_ok, unwrap
from temper.tools import TOOLS, call

# 加载环境变量
load_dotenv()

# ==================== 对话记忆系统 ====================
conversation_history = []  # 持久化对话历史
MAX_HISTORY = 20           # 保留最近 20 轮对话

def get_messages_with_history(current_input):
    """构建包含历史的 messages"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 添加历史记录（限制长度）
    if conversation_history:
        # 只保留最近 MAX_HISTORY 轮
        recent_history = conversation_history[-MAX_HISTORY*2:]  # *2 因为每轮有 user + assistant
        messages.extend(recent_history)

    # 添加当前输入
    messages.append({"role": "user", "content": current_input})
    return messages

def add_to_history(user_input, assistant_response):
    """添加一轮对话到历史"""
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": assistant_response})

    # 清理过旧的历史（保留最近 MAX_HISTORY 轮）
    while len(conversation_history) > MAX_HISTORY * 2:
        conversation_history.pop(0)

def clear_history():
    """清空对话历史"""
    global conversation_history
    conversation_history = []
    return "对话历史已清空"

def get_history_info():
    """获取历史统计信息"""
    rounds = len(conversation_history) // 2
    return f"当前对话历史: {rounds} 轮 (最多保留 {MAX_HISTORY} 轮)"

# ====================================================

# 检查 API Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 错误：未找到 DASHSCOPE_API_KEY")
    print("请创建 .env 文件并写入: DASHSCOPE_API_KEY=sk-你的密钥")
    sys.exit(1)

# 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://coding.dashscope.aliyuncs.com/v1"
)

# 系统提示词（Codong 风格）
SYSTEM_PROMPT = """你是 Temper，一个 AI 原生的 Coding Agent。

## 可用工具

使用 `tool` 字段指定工具名，支持以下工具：

### fs 模块（文件系统）
- {"tool": "fs.read", "args": {"path": "文件名"}} — 读取文件
- {"tool": "fs.write", "args": {"path": "文件名", "content": "内容"}} — 写入文件
- {"tool": "fs.edit", "args": {"path": "文件名", "old_string": "原内容", "new_string": "新内容"}} — 编辑文件
- {"tool": "fs.exists", "args": {"path": "文件名"}} — 检查存在
- {"tool": "fs.list", "args": {"path": "."}} — 列出目录
- {"tool": "fs.read_json", "args": {"path": "文件名"}} — 读取 JSON

### shell 模块（命令执行）
- {"tool": "shell.run", "args": {"cmd": "命令"}} — 执行 shell 命令

### self 模块（自我修改 - 带测试+回滚）
- {"tool": "self.edit_safe", "args": {"path": "文件名", "old_string": "原内容", "new_string": "新内容", "verify": true}} — 安全编辑（自动备份+语法检查+测试+失败回滚）
- {"tool": "self.list_backups", "args": {}} — 列出所有备份
- {"tool": "self.restore", "args": {"path": "原文件名", "timestamp": "备份时间戳"}} — 恢复到指定备份
- {"tool": "self.cleanup", "args": {"keep": 10}} — 清理旧备份（默认保留最近10个）

## 重要规则

1. **一次只能调用一个工具**
2. **严格 JSON 格式**：{"tool": "...", "args": {...}}
3. **错误处理**：如果工具返回 {"ok": false, "error": "..."}，分析错误信息并尝试修复
4. **自我修改推荐用 self.edit_safe**（带自动备份和回滚），只有在确定不需要验证时才用 fs.edit
5. **回滚机制**：self.edit_safe 会自动验证语法和运行测试，如果失败会自动回滚到备份

## 输出格式

需要调用工具时，只输出 JSON：
{"tool": "fs.read", "args": {"path": "temper.py"}}

不需要调用工具时，直接回复自然语言。
"""

def format_result(result, max_length=8000):
    """格式化工具结果（给模型看）
    
    Args:
        result: 工具执行结果（ok/error 格式）
        max_length: 内容最大长度限制
    
    Returns:
        JSON 字符串，已处理过长内容的截断
    """
    if is_error(result):
        # 错误返回详细信息
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    # 成功返回内容
    value = unwrap(result)
    
    # 智能截断处理
    if isinstance(value, str):
        if len(value) > max_length:
            # 尝试在换行处截断，保持可读性
            truncated = value[:max_length]
            last_newline = truncated.rfind('\n')
            if last_newline > max_length * 0.8:  # 如果最后换行在80%之后
                truncated = truncated[:last_newline]
            value = truncated + "\n... [内容过长，已截断，共 " + str(len(value)) + " 字符]"
    elif isinstance(value, (list, dict)):
        # 对于复杂类型，先序列化再检查长度
        serialized = json.dumps(value, ensure_ascii=False, indent=2)
        if len(serialized) > max_length:
            # 简化输出：只保留前N个元素/键
            if isinstance(value, list) and len(value) > 100:
                value = value[:100] + [f"... [还有 {len(value) - 100} 个元素未显示]"]
            elif isinstance(value, dict) and len(value) > 50:
                # 保留前50个键
                items = list(value.items())[:50]
                value = dict(items)
                value["__truncated__"] = f"... [还有 {len(value) - 50} 个键未显示]"
    
    return json.dumps({"ok": True, "value": value}, ensure_ascii=False, indent=2)

def chat(user_input):
    """主对话循环（带记忆）"""
    # 构建包含历史的 messages
    messages = get_messages_with_history(user_input)
    initial_length = len(messages)

    max_rounds = 20  # 单次最大工具调用轮数
    full_response = []  # 收集完整响应

    for round_num in range(max_rounds):
        # 调用模型
        response = client.chat.completions.create(
            model="kimi-k2.5",
            messages=messages,
            temperature=0.6,
            max_tokens=8192
        )

        content = response.choices[0].message.content
        full_response.append(content)
        print(f"\n🤖 Temper: {content[:2000]}{'...' if len(content) > 2000 else ''}")

        # 检查是否需要调用工具
        try:
            if '"tool":' in content:
                # 提取 JSON 工具调用
                start = content.find('{')
                end = content.rfind('}') + 1
                tool_call = json.loads(content[start:end])

                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})

                print(f"\n🔧 调用: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

                # 执行工具
                result = call(tool_name, **tool_args)

                # 显示结果摘要
                if is_error(result):
                    print(f"❌ 错误: {result.get('error')} - {result.get('message')}")
                else:
                    value = unwrap(result)
                    preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"✅ 结果: {preview}")

                # 添加到对话历史（工具调用轮）
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": format_result(result)})
                continue

        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析错误: {e}")
        except Exception as e:
            print(f"⚠️ 工具执行错误: {e}")

        # 没有工具调用，结束本轮
        break

    # 保存到对话历史（合并所有响应）
    final_response = "\n".join(full_response)
    add_to_history(user_input, final_response)

def main():
    """主入口"""
    print("=" * 50)
    print("🧊 Temper Evolve v2.0")
    print("Codong 风格重构版")
    print("=" * 50)
    print()
    print("命令:")
    print("  /clear   - 清空对话历史")
    print("  /history - 查看历史长度")
    print("  tools    - 查看可用工具")
    print("  exit     - 退出")
    print()

    while True:
        try:
            user_input = input("👤 你: ").strip()

            if user_input.lower() == 'exit':
                print("\n👋 再见！")
                break

            if user_input.lower() == 'tools':
                print("\n📦 可用工具:")
                for name in sorted(TOOLS.keys()):
                    print(f"  - {name}")
                print()
                continue

            if user_input.lower() == '/clear':
                print(f"\n🗑️  {clear_history()}")
                print()
                continue

            if user_input.lower() == '/history':
                print(f"\n📜 {get_history_info()}")
                print()
                continue

            if not user_input:
                continue

            chat(user_input)

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
