import os
import json
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 文件
load_dotenv()

# 从环境变量读取 Key
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    print("❌ 错误：没有找到 DASHSCOPE_API_KEY")
    print("")
    print("请创建 .env 文件，写入：")
    print("DASHSCOPE_API_KEY=sk-你的密钥")
    print("")
    print("然后在 PowerShell 运行：pip install python-dotenv")
    exit(1)

client = OpenAI(
    api_key=api_key,
    base_url="https://coding.dashscope.aliyuncs.com/v1"
)

SYSTEM_PROMPT = """你是 Temper，一个自进化的 coding agent。

你有两个工具：
- read_file(path) — 读取文件内容
- run_bash(command) — 执行 shell 命令

用户会给你任务，你需要：
1. 分析需要做什么
2. 使用工具完成
3. 简洁汇报结果

工具调用格式（严格 JSON）：
{"tool": "read_file", "args": {"path": "xxx"}}
或
{"tool": "run_bash", "args": {"command": "xxx"}}
"""

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def run_bash(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

TOOLS = {
    "read_file": read_file,
    "run_bash": run_bash
}

def chat(user_input):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]
    
    for _ in range(5):
        response = client.chat.completions.create(
            model="kimi-k2.5",
            messages=messages,
            temperature=0.2
        )
        
        content = response.choices[0].message.content
        print(f"\n🤖 Temper: {content}")
        
        try:
            if '{"tool":' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                tool_call = json.loads(content[start:end])
                
                tool_name = tool_call["tool"]
                tool_args = tool_call["args"]
                
                print(f"\n🔧 调用: {tool_name}({tool_args})")
                
                result = TOOLS[tool_name](**tool_args)
                print(f"📤 结果: {result[:200]}..." if len(result) > 200 else f"📤 结果: {result}")
                
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"工具返回: {result[:1000]}"})
                continue
        except Exception as e:
            print(f"工具解析错误: {e}")
        
        break

if __name__ == "__main__":
    print("🧊 Temper Agent 启动 (DashScope / 通义千问)")
    print("输入 'exit' 退出\n")
    
    while True:
        user_input = input("👤 你: ")
        if user_input.lower() == 'exit':
            break
        chat(user_input)