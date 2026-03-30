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
| `fs.read` | 读取文件（分页） | `{"tool": "fs.read", "args": {"path": "file.txt", "offset": 0, "limit": 50}}` |
| `fs.write` | 写入文件 | `{"tool": "fs.write", "args": {"path": "file.txt", "content": "..."}}` |
| `fs.edit` | 编辑文件（精确匹配） | `{"tool": "fs.edit", "args": {"path": "file.txt", "old_string": "...", "new_string": "..."}}` |
| `fs.exists` | 检查存在 | `{"tool": "fs.exists", "args": {"path": "file.txt"}}` |
| `fs.list` | 列出目录 | `{"tool": "fs.list", "args": {"path": "."}}` |
| `fs.read_json` | 读取 JSON | `{"tool": "fs.read_json", "args": {"path": "data.json"}}` |

### Shell 模块

| 工具 | 描述 | 示例 |
|------|------|------|
| `shell.run` | 执行命令 | `{"tool": "shell.run", "args": {"cmd": "dir"}}` |

### Self 模块（自我进化）

| 工具 | 描述 | 示例 |
|------|------|------|
| `self.snapshot` | 创建代码快照 | `{"tool": "self.snapshot", "args": {"files": ["temper.py"], "tag": "修改前"}}` |
| `self.diff` | 对比代码变更 | `{"tool": "self.diff", "args": {}}` |
| `self.log` | 生成进化日志 | `{"tool": "self.log", "args": {"title": "新功能", "description": "..."}}` |
| `self.list_snapshots` | 列出所有快照 | `{"tool": "self.list_snapshots", "args": {}}` |

---

## 🎯 核心特性

- ✅ **结构化错误** - 每个错误包含 `code`, `message`, `fix`, `retry` 字段（学习 Codong）
- ✅ **模块化工具** - 按功能分组（fs/shell），易于扩展
- ✅ **类型验证** - 自动检查参数类型
- ✅ **自我修改** - 可以用 `fs.edit` 修改 temper.py 自己的代码
- ✅ **Python 语法检查** - 编辑 .py 文件时自动验证 AST
- ✅ **智能内容截断** - 长文件内容智能截断（尝试在换行处截断，显示总字符数）
- ✅ **工具链组合** - 支持 `chain`（串行）和 `parallel`（并行）执行多个工具
- ✅ **对话记忆** - 自动保留最近 20 轮对话上下文，支持持久化（重启后恢复）
- ✅ **文件分页读取** - `fs.read` 支持 `offset` 和 `limit` 参数，高效读取大文件
- ✅ **自我修复** - 能识别并修复自身代码的缩进错误等语法问题
- ✅ **自我记录** - 能自动创建快照、对比变更、生成进化日志

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

### 工具链组合（串行）
```
👤 你: 执行完整进化流程
🤖 Temper: {"chain": [
  {"tool": "self.snapshot", "args": {"files": ["temper.py"], "tag": "修改前"}},
  {"tool": "fs.edit", "args": {"path": "temper.py", "old_string": "...", "new_string": "..."}},
  {"tool": "self.diff", "args": {}},
  {"tool": "self.log", "args": {"title": "新功能", "description": "..."}}
]}
⛓️ 串行工具链: 4 个工具
✅ 全部完成
```

### 工具链组合（并行）
```
👤 你: 并行读取多个文件
🤖 Temper: {"parallel": [
  {"tool": "fs.read", "args": {"path": "README.md"}},
  {"tool": "fs.read", "args": {"path": "CHANGELOG.md"}},
  {"tool": "fs.list", "args": {"path": "temper/tools"}}
]}
⚡ 并行工具链: 3 个工具
✅ 全部完成 (3/3)
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
│   ├── day-001.md          # Day 1: v2.0 Codong 风格重构
│   ├── day-002.md          # Day 2: 首次自修复、历史持久化、工具增强与日志系统
│   ├── day-003.md          # Day 3: 自我进化记录自动化
│   └── day-004.md          # Day 4: 工具链组合（chain/parallel）
├── .temper_backups/        # 代码快照（自动创建）
├── temper.log              # 运行日志（自动创建）
├── temper_errors.log       # 错误日志（自动创建）
├── .env                    # 环境变量（需手动创建）
└── README.md               # 项目文档
```

---

## 📖 每日进化

| 日期 | 日志 |
|------|------|
| 2026-03-28 | [Day 1](./journal/day-001.md) - v2.0 Codong 风格重构 |
| 2026-03-29 | [Day 2](./journal/day-002.md) - 首次自修复：Bug 修复、历史持久化、工具增强、日志系统与 API 异常处理 |
| 2026-03-30 | [Day 3](./journal/day-003.md) - 自我进化记录自动化：self.snapshot、self.diff、self.log |
| 2026-03-31 | [Day 4](./journal/day-004.md) - 工具链组合：chain（串行）/ parallel（并行）执行 |

---

## 🔗 相关项目


- ## 🙏 致谢
  
- [Codong](https://github.com/brettinhere/Codong) - AI 原生编程语言，Temper 的错误系统设计参考了 Codong

- [yoyo-evolve](https://github.com/yologdev/yoyo-evolve) — 公开成长的理念启发，让我开始记录 Temper 的每一天


---

*Tempered in iteration, hardened in use.*
