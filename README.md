# 🧊 Temper Evolve

> 一个自进化的 Coding Agent，每天记录成长。

---

## ✨ 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Renu-Cybe/temper-evolve.git
cd temper-evolve
```

### 2. 安装依赖

```bash
pip install openai python-dotenv
```

### 3. 配置 API Key

```bash
notepad .env
```

写入你的阿里云百炼 API Key：

```env
DASHSCOPE_API_KEY=sk-你的密钥
```

### 4. 启动 Temper

```bash
python temper.py
```

---

## 🚀 使用方法

启动后会看到：

```
🧊 Temper Agent 启动 (DashScope / 通义千问)
输入 'exit' 退出

👤 你:
```

直接输入自然语言指令，例如：

| 指令 | 说明 |
|------|------|
| `看一下当前目录` | 列出文件 |
| `读取 README.md` | 查看文件内容 |
| `当前目录有什么文件` | 探索文件系统 |
| `exit` | 退出程序 |

### 示例对话

```
👤 你: 看一下当前目录有什么文件

🤖 Temper: {"tool": "run_bash", "args": {"command": "dir"}}

🔧 调用: run_bash({'command': 'dir'})
📤 结果:
  驱动器 C 中的卷是 系统
  ...
  temper.py
  README.md

🤖 Temper: 当前目录包含 temper.py 和 README.md 等文件
```

---

## 🛠️ 可用工具

| 工具 | 功能 |
|------|------|
| `read_file(path)` | 读取文件内容 |
| `run_bash(command)` | 执行 shell 命令 |
| `edit_file(path, old_string, new_string)` | **修改文件内容**（支持自修复） |

## ✨ 当前功能

- ✅ **读取文件** (`read_file`)
- ✅ **执行命令** (`run_bash`)
- ✅ **修改文件** (`edit_file`) - Temper 现在可以修改自己的代码！
- ✅ **多轮对话**
- ✅ **工具调用链**（最多 5 轮）

## ⚠️ 已知限制

- 单次只能处理一个工具调用
- 无对话历史保存（重启后丢失）

---

## 📁 项目结构

```
temper-evolve/
├── temper.py          # 主程序
├── .env               # API Key（不提交到 Git）
├── .gitignore         # 忽略 .env
├── journal/           # 进化日志
│   └── day-001.md
└── README.md          # 本文件
```

---

## 📖 每日进化

查看 [`journal/`](./journal/) 目录了解 Temper 的成长记录。

| 日期 | 日志 |
|------|------|
| 2026-03-28 | [Day 1](./journal/day-001.md) - 骨架搭建 + 获得「自我修改」能力 |

---

*Tempered in iteration, hardened in use.*
