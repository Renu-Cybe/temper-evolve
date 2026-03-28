# 🧊 Temper Evolve v2.0

> 自进化 Coding Agent，采用 Codong 风格的结构化错误处理

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

创建 `.env` 文件：

```bash
# Windows
notepad .env

# Linux/Mac
touch .env
```

写入你的阿里云百炼 API Key：

```env
DASHSCOPE_API_KEY=sk-你的密钥
```

### 4. 启动 Temper

```bash
python temper.py
```

启动后输入 `tools` 查看可用工具。

### 内置命令

| 命令 | 功能 |
|------|------|
| `tools` | 查看可用工具 |
| `/clear` | 清空对话历史 |
| `/history` | 查看当前历史长度 |
| `exit` | 退出程序 |

### 对话记忆

Temper 会自动保留最近 **20 轮**对话历史，你可以：
- 引用之前的内容继续对话
- 使用 `/clear` 清空历史
- 使用 `/history` 查看当前历史长度

---

## ⚙️ 配置

创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=sk-你的密钥
```

---

## 🛠️ 可用工具

### FS 模块（文件系统）

| 工具 | 描述 | 示例 |
|------|------|------|
| `fs.read` | 读取文件 | `{"tool": "fs.read", "args": {"path": "file.txt"}}` |
| `fs.write` | 写入文件 | `{"tool": "fs.write", "args": {"path": "file.txt", "content": "..."}}` |
| `fs.edit` | 编辑文件（精确匹配） | `{"tool": "fs.edit", "args": {"path": "file.txt", "old_string": "...", "new_string": "..."}}` |
| `fs.exists` | 检查存在 | `{"tool": "fs.exists", "args": {"path": "file.txt"}}` |
| `fs.list` | 列出目录 | `{"tool": "fs.list", "args": {"path": "."}}` |
| `fs.read_json` | 读取 JSON | `{"tool": "fs.read_json", "args": {"path": "data.json"}}` |

### Shell 模块

| 工具 | 描述 | 示例 |
|------|------|------|
| `shell.run` | 执行命令 | `{"tool": "shell.run", "args": {"cmd": "dir"}}` |

---

## 🎯 核心特性

- ✅ **结构化错误** - 每个错误包含 `code`, `message`, `fix`, `retry` 字段（学习 Codong）
- ✅ **模块化工具** - 按功能分组（fs/shell），易于扩展
- ✅ **类型验证** - 自动检查参数类型
- ✅ **自我修改** - 可以用 `fs.edit` 修改 temper.py 自己的代码
- ✅ **Python 语法检查** - 编辑 .py 文件时自动验证 AST
- ✅ **智能内容截断** - 长文件内容智能截断（尝试在换行处截断，显示总字符数）
- ✅ **对话记忆** - 自动保留最近 20 轮对话上下文，支持持久化（重启后恢复）

---

## 💡 使用示例

### 读取文件
```
👤 你: 读取 README.md
🤖 Temper: {"tool": "fs.read", "args": {"path": "README.md"}}
🔧 调用: fs.read({"path": "README.md"})
✅ 结果: # 🧊 Temper Evolve v2.0...
```

### 自我修改
```
👤 你: 修改 temper.py，把 temperature 从 0.6 改成 0.8
🤖 Temper: {"tool": "fs.read", "args": {"path": "temper.py"}}
...（读取内容）...
🤖 Temper: {"tool": "fs.edit", "args": {"path": "temper.py", "old_string": "temperature=0.6", "new_string": "temperature=0.8"}}
🔧 调用: fs.edit(...)
✅ 结果: 成功修改 temper.py
```

### 对话记忆（多轮对话）
```
👤 你: 读取 README.md
🤖 Temper: {"tool": "fs.read", "args": {"path": "README.md"}}
✅ 结果: # 🧊 Temper Evolve v2.0...

👤 你: 总结一下刚才的内容      ← 有上下文记忆！
🤖 Temper: 这是 Temper v2.0 的说明文档，主要特性包括...

👤 你: 再详细说说第一点
🤖 Temper: 结构化错误是指...

👤 你: /history
📜 当前对话历史: 3 轮 (最多保留 20 轮)
```

---

## 📁 项目结构

```
temper-evolve/
├── temper/                  # 核心包
│   ├── core/               # 核心模块
│   │   ├── errors.py       # 结构化错误系统
│   │   └── types.py        # 类型验证
│   └── tools/              # 工具模块
│       ├── fs.py           # 文件系统
│       └── shell.py        # 命令执行
├── temper.py               # 主入口
├── journal/                # 进化日志
│   └── day-001.md
└── README.md
```

---

## 📖 每日进化

| 日期 | 日志 |
|------|------|
| 2026-03-28 | [Day 1](./journal/day-001.md) - v2.0 Codong 风格重构 |
| 2026-03-28 | [Day 2](./journal/day-002.md) - 首次自修复：Bug 修复与历史持久化 |

---

## 🔗 相关项目

- [Codong](https://github.com/brettinhere/Codong) - AI 原生编程语言，Temper 的错误系统设计参考了 Codong

---

*Tempered in iteration, hardened in use.*
