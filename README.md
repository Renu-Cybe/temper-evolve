# 🧊 Temper Evolve v3.0 - 四自系统

**版本：** 3.0.0  
**更新：** 2026-04-03 - 完整优化版  
**测试：** 29/29 通过 ✓

AI 原生 Coding Agent，实现完整的四自系统（自感知、自适应、自组织、自编译），严格遵循铁三角原则。

## 🎯 四自系统

### 1. 自感知（Self-Awareness）
- **健康自检**：系统级健康检查，监控所有模块状态
- **资源监控**：CPU、内存、磁盘、网络实时监控
- **依赖检查**：外部 API、文件、服务依赖验证
- **健康报告**：结构化健康报告生成

### 2. 自适应（Self-Adaptive）
- **动态调参**：根据负载自动调整系统参数
- **性能优化**：基于指标自动生成优化建议
- **限流控制**：令牌桶限流 + 熔断器模式
- **配置热更新**：运行时配置更新，无需重启

### 3. 自组织（Self-Organizing）
- **工作流定义**：声明式工作流定义，支持链式调用
- **任务编排**：串行、并行、条件任务执行
- **依赖解析**：拓扑排序，自动解析任务依赖
- **动态合成**：根据条件动态合成工作流

### 4. 自编译（Self-Compiling）
- **代码模板**：支持变量插值、条件渲染、循环
- **代码生成**：运行时代码生成和编译
- **自我修复**：自动检测并修复代码问题
- **热加载**：模块热加载，无需重启

## 🔺 铁三角原则

### 信任原则（Trust）
- ✅ **透明可审计**：所有操作记录审计日志
- ✅ **不擅自修改用户文件**：修改前必须创建备份
- ✅ **操作可回溯**：支持操作历史查询和回滚
- ✅ **日志不可篡改**：使用哈希链保证日志完整性

### 复利原则（Compound）
- 💰 **能力持久化**：系统状态自动保存和恢复
- 💰 **下次启动继承**：持久化数据跨会话保留
- 💰 **增量更新**：支持增量保存，提高效率
- 💰 **版本迁移**：数据版本自动迁移

### 杠杆原则（Leverage）
- ⚙️ **配置驱动**：所有行为通过配置控制
- ⚙️ **拒绝硬编码**：零硬编码，完全可配置
- ⚙️ **配置分层**：默认/用户/运行时三层配置
- ⚙️ **热加载配置**：运行时更新配置无需重启

## 💓 心跳进化器（2026-04-01 新增）

### 核心功能

**让四自系统真正"活"起来：**

| 行为 | 频率 | 说明 |
|------|------|------|
| **自感知** | 每 60 秒 | 资源检查 + 异常告警 |
| **自适应** | 每 5 分钟 | 参数调优建议 |
| **自编译** | 每 1 小时 | 代码问题扫描 |

### v3.0 增强（2026-04-03）

**事件驱动集成：**

```
TemperEvolver → EventBus → [审计日志 + 持久化 + 四自模块]
```

- ✅ 所有心跳操作发布事件
- ✅ 事件链接到审计系统
- ✅ 统计数据持久化保存
- ✅ 支持事件处理器注册

### 使用方法

```
/evolver        # 查看状态
/evolver start  # 启动进化器
/evolver stop   # 停止进化器
/evolver debug  # 切换调试模式
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `self_check_interval` | 60s | 自检间隔 |
| `adapt_interval` | 300s | 自适应间隔 |
| `repair_check_interval` | 3600s | 修复检查间隔 |
| `auto_repair_enabled` | False | 自动修复（安全优先）|
| `debug` | False | 调试输出 |

---

## 🧠 上下文管理系统（2026-04-01 新增）

### 三层架构

基于 Claude Code 的上下文工程最佳实践：

| 层级 | 内容 | Token 预算 |
|------|------|-----------|
| **L1: 系统层** | 核心指令、工具定义、安全规则 | 20% |
| **L2: 项目层** | Skills、CLAUDE.md、MCP tools | 30% |
| **L3: 会话层** | 对话历史、运行状态、中间结果 | 28% |

### 核心特性

- **Token 预算管理**：22% 预留给自动压缩
- **按需加载 Skills**：减少上下文占用
- **上下文压缩**：自动清理工具结果

### 使用示例

```python
from temper.context import ContextManager

manager = ContextManager()

# 添加系统层内容
manager.add_system_content("core", "You are Temper Agent...", 100)

# 按需加载 Skill
manager.load_project_skill("heartbeat_evolver")

# 添加会话层内容
manager.add_session_content("query", "Check health", 20)

# 构建上下文
context = manager.build_context()

# 压缩会话层
manager.compact_session_layer(keep_last_n=10)
```

---

## 📝 输出格式系统（2026-04-01 新增）

### 内置样式

| 样式 | 用途 |
|------|------|
| **Default** | 标准软件工程模式，高效完成任务 |
| **Explanatory** | 教育模式，提供 Insights 解释实现选择 |
| **Learning** | 学习模式，交互式编程，添加 TODO(human) |

### 结构化输出

强制 JSON Schema 输出：

```python
from temper.output import OutputStyleManager, OutputStyle

manager = OutputStyleManager()

# 设置结构化输出
manager.set_structured_output({
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "issues": {"type": "array"}
    }
})

# 格式化输出
result = manager.format_output({"status": "healthy", "issues": []})
# => {"ok": True, "value": {"status": "healthy", "issues": []}}
```

### 自定义样式

```python
manager.create_custom_style(
    "temper_heartbeat",
    "Focus on heartbeat evolution tasks",
    "Heartbeat evolution mode"
)
```

---

## 📁 项目结构

```
temper/
├── temper.py                    # 主入口
├── README.md                    # 说明文档
├── OPTIMIZATION_SUMMARY.md      # v3.0 优化总结（新增）
├── journal/
│   ├── day-006.md              # 心跳进化器实现
│   └── day-007.md              # v3.0 完整优化（新增）
├── tests/                       # 测试套件（新增）
│   ├── test_result.py          # 错误处理测试
│   ├── test_events.py          # 事件系统测试
│   └── test_config.py          # 配置系统测试
├── .temper/
│   └── config.json             # 默认配置
└── temper/
    ├── core/                   # 核心模块
    │   ├── result.py           # Codong 错误处理（v3.0 重写）
    │   ├── events.py           # 事件系统
    │   ├── self_awareness.py   # 自感知
    │   ├── self_adaptive.py    # 自适应
    │   ├── self_organizing.py  # 自组织
    │   └── self_compiling.py   # 自编译
    ├── config/                 # 配置系统（杠杆原则）
    │   ├── manager.py
    │   └── schema.py           # HeartbeatConfig（新增）
    ├── audit/                  # 审计系统（信任原则）
    │   ├── logger.py
    │   └── tracer.py
    ├── heartbeat/              # 💓 心跳进化器
    │   ├── __init__.py
    │   └── evolver.py          # v3.0 事件驱动增强
    └── __main__.py             # 主入口
```

## 🚀 快速开始

### 1. 启动系统

```bash
python3 temper.py
```

### 2. 可用命令

```
/status          - 查看系统状态
/metrics         - 查看系统指标
/health          - 查看健康状态
/config          - 查看/修改配置
/snapshot        - 创建/恢复快照
/audit           - 查看审计日志
/repair          - 代码修复
/generate        - 代码生成
/evolver         - 心跳进化器控制（新增）
/evolver start   - 启动进化器
/evolver stop    - 停止进化器
/evolver debug   - 切换调试模式
/clear           - 清空对话历史
exit             - 退出
```

### 3. 编程接口

```python
from temper.core import (
    get_four_self_system,
    create_workflow, parallel_tasks,
    quick_health_check
)

# 初始化系统
system = get_four_self_system()
system.initialize()

# 健康检查
result = system.health_check()
if result['ok']:
    report = result['value']
    print(f"状态: {report.status}")

# 创建工作流
workflow = create_workflow("我的工作流")
workflow.add_task("task1", lambda: ok("结果1"))
workflow.add_task("task2", lambda: ok("结果2"), dependencies=["task1"])

# 运行工作流
result = system.run_workflow(workflow)

# 并行任务
result = parallel_tasks([task1, task2, task3])
```

## 🛡️ Codong 错误处理风格

所有函数遵循 Codong 错误处理风格：

```python
# 成功返回
return {"ok": True, "value": 返回值}

# 错误返回
return {"ok": False, "error": "ERROR_CODE", "message": "详细错误信息"}

# 检查错误
if is_error(result): ...

# 提取值
value = unwrap(result, default=None)
```

### v3.0 统一错误处理（2026-04-03）

**新增功能：**

```python
from temper.core import ErrorCode, CodongError

# 使用 ErrorCode 枚举
err(ErrorCode.VALIDATION_ERROR, "验证失败")

# 带详细信息
err(ErrorCode.FILE_NOT_FOUND, "文件不存在", {"path": "/tmp/test.txt"})

# 函数式操作
result = ok(5)
result = bind_result(result, lambda x: ok(x * 2))  # Chain
result = map_result(result, lambda x: x + 1)      # Map

# 异常捕获
result = try_catch(lambda: 10 / 0, "DIVISION_ERROR")

# 抛出异常
value = unwrap_or_raise(result)  # 错误时抛出 CodongError
```

**便捷错误函数：**

```python
file_not_found("/tmp/test.txt")
network_error("https://api.example.com", "连接拒绝")
timeout_error("API 调用", 30.0)
validation_error("name", "不能为空")
not_found("User", "123")
```

## 📊 系统要求

- Python 3.8+
- 仅使用 Python 标准库
- 无外部依赖

## 📜 许可证

MIT License

---

## 📅 更新日志

### 2026-04-03 - v3.0.0 - 完整优化版

**五阶段优化完成：**

| 阶段 | 内容 | 测试 |
|------|------|------|
| Phase 1 | 统一错误处理 | 18/18 ✓ |
| Phase 2 | 重构模块结构 | - |
| Phase 3 | 增强心跳集成（事件驱动） | - |
| Phase 4 | 统一配置系统 | 11/11 ✓ |
| Phase 5 | 添加测试覆盖 | 29/29 ✓ |

**核心变更：**

- ✅ 重写 `temper/core/result.py` - 统一 Codong 错误处理
- ✅ 删除 `temper/core/errors.py` - 消除 ~400 行重复代码
- ✅ 新增事件系统集成 - 心跳进化器链接审计/持久化
- ✅ 新增 `HeartbeatConfig` - 合并到主配置系统
- ✅ 新增测试套件 - 29 个单元测试

**新增文件：**
- `tests/test_result.py` - 错误处理测试
- `tests/test_events.py` - 事件系统测试
- `tests/test_config.py` - 配置系统测试
- `journal/day-007.md` - v3.0 优化日志

**铁三角原则实现：**

| 原则 | 实现 |
|------|------|
| 信任 | 事件驱动审计日志 |
| 复利 | 心跳统计持久化 |
| 杠杆 | 配置统一管理 |

---

### 2026-04-01 - v3.0.1

**新增：心跳进化器**

- ✅ 新增 `temper/heartbeat/` 模块
- ✅ `TemperEvolver` 类实现定时触发四自行为
- ✅ 新增 `/evolver` 命令（start/stop/debug）
- ✅ 测试脚本 `test_simple.py` 验证通过
- ✅ 更新 journal/day-006.md 记录开发过程

**解决的问题：**

用户反馈"四自系统代码存在但感受不到运行"，通过添加心跳循环让系统真正"活"起来。
