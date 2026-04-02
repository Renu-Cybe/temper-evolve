#!/usr/bin/env python3
"""
🧊 Temper Evolve v3.0 - 四自系统版

AI 原生 Coding Agent，结构化错误处理，模块化工具系统
"""

import os
import sys
import json
import logging
import traceback
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from openai import OpenAI

from temper.core import (
    ok, err, is_error, is_ok, unwrap, ErrorCode,
    # 四自系统
    FourSelfSystem, get_four_self_system,
    quick_health_check, create_health_report,
    create_workflow, run_workflow, serial_tasks, parallel_tasks,
)
from temper.tools import TOOLS, call, call_chain, call_parallel
from temper.heartbeat import TemperEvolver, EvolverConfig


class TemperApp:
    """Temper 应用封装类
    
    解决全局状态管理问题，提供统一的应用程序接口
    """
    
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # Windows 控制台 UTF-8 支持
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        # 初始化日志系统
        self.logger = self.setup_logging()
        
        # 初始化四自系统
        self.four_self_system = get_four_self_system()
        self.four_self_system.initialize()
        
        # 初始化 API 客户端
        self.client = self._init_client()
        
        # 初始化对话历史
        self.conversation_history = []
        self.max_history = 20
        self.history_file = ".temper_history.json"
        self.load_history()
        
        # 初始化心跳进化器
        self.evolver = None
        
        # 系统提示词
        self.system_prompt = SYSTEM_PROMPT
        
    def setup_logging(self):
        """配置日志系统"""
        LOG_FILE = "temper.log"
        ERROR_LOG_FILE = "temper_errors.log"

        # 主日志 - 只写入文件，不输出到控制台
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
            ]
        )

        # 错误日志 - 仅记录错误和异常
        error_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8', mode='a')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s\n%(exc_info)s'
        ))

        logger = logging.getLogger('temper')
        logger.addHandler(error_handler)
        return logger

    def log_exception(self, e, context=""):
        """记录异常详细信息"""
        error_msg = f"""
{'='*60}
异常时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
上下文: {context}
异常类型: {type(e).__name__}
异常信息: {str(e)}
堆栈跟踪:
{traceback.format_exc()}
{'='*60}
"""
        self.logger.error(error_msg)
        return error_msg

    def _init_client(self):
        """初始化 API 客户端"""
        # 检查 API Key
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ 错误：未找到 DASHSCOPE_API_KEY")
            print("请创建 .env 文件并写入: DASHSCOPE_API_KEY=sk-你的密钥")
            sys.exit(1)

        # 初始化客户端
        return OpenAI(
            api_key=api_key,
            base_url="https://coding.dashscope.aliyuncs.com/v1"
        )

    # ==================== 对话记忆系统 ====================

    def load_history(self):
        """从文件加载对话历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = data.get('history', [])
                    self.logger.info(f"已加载 {len(self.conversation_history)//2} 轮历史对话")
                    print(f"📂 已加载 {len(self.conversation_history)//2} 轮历史对话")
        except Exception as e:
            self.log_exception(e, "加载历史失败")
            print(f"⚠️ 加载历史失败: {e}")
            self.conversation_history = []

    def save_history(self):
        """保存对话历史到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({'history': self.conversation_history}, f, ensure_ascii=False, indent=2)
            self.logger.info(f"历史已保存，当前 {len(self.conversation_history)//2} 轮对话")
        except Exception as e:
            self.log_exception(e, "保存历史失败")
            print(f"⚠️ 保存历史失败: {e}")

    def get_messages_with_history(self, current_input):
        """构建包含历史的 messages"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加历史记录（限制长度）
        if self.conversation_history:
            # 只保留最近 MAX_HISTORY 轮
            recent_history = self.conversation_history[-self.max_history*2:]  # *2 因为每轮有 user + assistant
            messages.extend(recent_history)

        # 添加当前输入
        messages.append({"role": "user", "content": current_input})
        return messages

    def add_to_history(self, user_input, assistant_response):
        """添加一轮对话到历史"""
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        # 清理过旧的历史（保留最近 MAX_HISTORY 轮）
        while len(self.conversation_history) > self.max_history * 2:
            self.conversation_history.pop(0)
        
        # 持久化到文件
        self.save_history()

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.save_history()  # 同步清空文件
        return "对话历史已清空"

    def get_history_info(self):
        """获取历史统计信息"""
        rounds = len(self.conversation_history) // 2
        return f"当前对话历史: {rounds} 轮 (最多保留 {self.max_history} 轮)"

    # ====================================================

    def format_result(self, result, max_length=8000):
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
                    original_len = len(value)
                    value = value[:100] + [f"... [还有 {original_len - 100} 个元素未显示]"]
                elif isinstance(value, dict) and len(value) > 50:
                    # 保留前50个键
                    original_len = len(value)
                    items = list(value.items())[:50]
                    value = dict(items)
                    value["__truncated__"] = f"... [还有 {original_len - 50} 个键未显示]"
        
        return json.dumps({"ok": True, "value": value}, ensure_ascii=False, indent=2)

    def chat(self, user_input):
        """主对话循环（带记忆）"""
        self.logger.info(f"用户输入: {user_input[:100]}...")
        
        try:
            # 构建包含历史的 messages
            messages = self.get_messages_with_history(user_input)
            initial_length = len(messages)
            self.logger.info(f"构建消息完成，共 {len(messages)} 条消息")

            max_rounds = 20  # 单次最大工具调用轮数
            full_response = []  # 收集完整响应

            for round_num in range(max_rounds):
                self.logger.info(f"开始第 {round_num + 1} 轮对话")
                
                # 调用模型
                try:
                    response = self.client.chat.completions.create(
                        model="kimi-k2.5",
                        messages=messages,
                        temperature=0.6,
                        max_tokens=8192
                    )
                    self.logger.info("API 调用成功")
                except Exception as e:
                    self.log_exception(e, f"API 调用失败 (第 {round_num + 1} 轮)")
                    print(f"❌ API 调用失败: {e}")
                    return

                content = response.choices[0].message.content
                full_response.append(content)

                # 检查是否需要调用工具
                try:
                    if '"tool":' in content:
                        # 使用 brace counting 精确提取第一个 JSON
                        start = content.find('{')
                        brace_count = 0
                        end = start
                        for i, char in enumerate(content[start:]):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end = start + i + 1
                                    break
                        json_str = content[start:end]
                        tool_call = json.loads(json_str)

                        # 检查是否是工具链调用
                        if "chain" in tool_call:
                            chain = tool_call.get("chain", [])
                            print(f"\n⛓️ chain: {len(chain)} 个工具")
                            result = call_chain(chain)
                        elif "parallel" in tool_call:
                            chain = tool_call.get("parallel", [])
                            print(f"\n⚡ parallel: {len(chain)} 个工具")
                            result = call_parallel(chain)
                        else:
                            # 单工具调用
                            tool_name = tool_call.get("tool")
                            tool_args = tool_call.get("args", {})
                            print(f"\n🔧 {tool_name}")
                            result = call(tool_name, **tool_args)

                        # 显示简短结果
                        if is_error(result):
                            print(f"❌ {result.get('error')}")
                        else:
                            print(f"✅ 完成")

                        # 添加到对话历史
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": self.format_result(result)})
                        continue

                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON 解析错误: {e}")
                except Exception as e:
                    print(f"⚠️ 工具执行错误: {e}")

                # 没有工具调用，显示回复
                print(f"\n🤖 {content}")
                break

        except Exception as e:
            self.log_exception(e, "chat 函数执行失败")
            print(f"❌ 对话处理失败: {e}")
            return

        # 保存到对话历史（合并所有响应）
        final_response = "\n".join(full_response)
        self.add_to_history(user_input, final_response)

    def start_evolver(self):
        """启动心跳进化器"""
        if self.evolver is None:
            config = EvolverConfig(
                self_check_interval=60,
                adapt_interval=300,
                repair_check_interval=3600,
                debug=False
            )
            self.evolver = TemperEvolver(self.four_self_system, config)
            self.evolver.start()
        
    def stop_evolver(self):
        """停止心跳进化器"""
        if self.evolver:
            self.evolver.stop()
            self.evolver = None

    def run(self):
        """运行主程序"""
        print("=" * 50)
        print("🧊 Temper Evolve v3.0 - 四自系统")
        print("DashScope + 四自系统")
        print("=" * 50)
        print()
        print("命令:")
        print("  health   - 健康检查")
        print("  status   - 系统状态")
        print("  adapt    - 自适应调整")
        print("  repair   - 自我修复")
        print("  workflow - 运行工作流")
        print("  tools    - 查看可用工具")
        print("  /clear   - 清空对话历史")
        print("  /history - 查看历史长度")
        print("  exit     - 退出")
        print()

        # 启动心跳进化器
        self.start_evolver()
        
        try:
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
                        print(f"\n🗑️  {self.clear_history()}")
                        print()
                        continue

                    if user_input.lower() == '/history':
                        print(f"\n📜 {self.get_history_info()}")
                        print()
                        continue

                    # 四自系统命令
                    if user_input.lower() == 'health':
                        result = self.four_self_system.health_check()
                        if is_error(result):
                            print(f"\n❌ {result.get('message')}")
                        else:
                            report = unwrap(result)
                            status = getattr(report, 'overall_status', 'unknown')
                            print(f"\n🏥 健康状态: {status}")
                        continue

                    if user_input.lower() == 'status':
                        result = self.four_self_system.get_status()
                        if is_error(result):
                            print(f"\n❌ {result.get('message')}")
                        else:
                            status = unwrap(result)
                            print(f"\n📊 系统状态: {status.get('initialized', False)}")
                        continue

                    if user_input.lower() == 'adapt':
                        print("\n🔄 执行自适应调整...")
                        result = self.four_self_system.adapt()
                        print(f"{'✅ 完成' if is_ok(result) else '❌ 失败'}")
                        continue

                    if user_input.lower() == 'repair':
                        print("\n🔧 执行自我修复...")
                        result = self.four_self_system.self_repair()
                        print(f"{'✅ 完成' if is_ok(result) else '❌ 失败'}")
                        continue

                    if user_input.lower() == 'workflow':
                        print("\n📋 运行示例工作流...")
                        wf = create_workflow("示例")
                        wf.add_task("t1", lambda: ok("步骤1"))
                        wf.add_task("t2", lambda: ok("步骤2"), dependencies=["t1"])
                        result = run_workflow(wf)
                        print(f"{'✅ 完成' if is_ok(result) else '❌ 失败'}")
                        continue

                    if not user_input:
                        continue

                    self.chat(user_input)

                except KeyboardInterrupt:
                    print("\n\n👋 再见！")
                    break
                except EOFError:
                    break
        finally:
            # 确保关闭心跳进化器
            self.stop_evolver()


# 系统提示词
SYSTEM_PROMPT = """你是 Temper，一个简洁的 AI Coding Agent。

## 可用工具

### fs 模块
- {"tool": "fs.read", "args": {"path": "文件名"}}
- {"tool": "fs.write", "args": {"path": "文件名", "content": "内容"}}
- {"tool": "fs.edit", "args": {"path": "文件名", "old_string": "原内容", "new_string": "新内容"}}
- {"tool": "fs.exists", "args": {"path": "文件名"}}
- {"tool": "fs.list", "args": {"path": "."}}

### shell 模块
- {"tool": "shell.run", "args": {"cmd": "命令"}}

## 规则

1. 一次只调用一个工具
2. 工具调用只输出 JSON，不要额外解释
3. 回复用中文，简洁直接，不要啰嗦

## 输出格式

调用工具时只输出 JSON：
{"tool": "fs.read", "args": {"path": "temper.py"}}

不调用工具时直接回复。
"""


def main():
    """主入口"""
    app = TemperApp()
    app.run()


if __name__ == "__main__":
    main()