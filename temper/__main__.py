#!/usr/bin/env python3
"""
🧊 Temper Evolve v3.0 - 四自系统版

AI 原生 Coding Agent，具备自感知、自适应、自组织、自编译能力
"""

import os
import sys
import signal
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# 核心组件
from temper.core.result import ok, err, is_ok, unwrap, ErrorCode
from temper.core.events import event_bus, Event, EventType

# 基础设施
from temper.config.manager import ConfigManager
from temper.config.schema import LogLevel
from temper.audit.logger import AuditLogger, AuditCategory, AuditLevel
from temper.audit.tracer import OperationTracer
from temper.persistence.snapshot import SnapshotManager

# 四自模块
from temper.self_awareness.metrics import MetricsCollector
from temper.self_awareness.resources import ResourceMonitor
from temper.self_awareness.diagnostics import Diagnostics, HealthStatus
from temper.self_adaptive.tuner import ParameterTuner
from temper.self_adaptive.strategies import StrategyEngine
from temper.self_organizing.workflow import WorkflowEngine
from temper.self_organizing.scheduler import TaskScheduler
from temper.self_compiling.repair import CodeRepair
from temper.self_compiling.generator import CodeGenerator

# 心跳进化器
from temper.heartbeat import TemperEvolver, EvolverConfig

# 加载环境变量
load_dotenv()


class TemperSystem:
    """Temper 系统主类"""
    
    def __init__(self):
        self._running = False
        
        # 基础设施
        self.config: ConfigManager = None
        self.audit: AuditLogger = None
        self.tracer: OperationTracer = None
        self.snapshots: SnapshotManager = None
        
        # 四自模块
        self.metrics: MetricsCollector = None
        self.monitor: ResourceMonitor = None
        self.diagnostics: Diagnostics = None
        self.tuner: ParameterTuner = None
        self.strategy_engine: StrategyEngine = None
        self.workflow_engine: WorkflowEngine = None
        self.code_repair: CodeRepair = None
        self.code_generator: CodeGenerator = None
        
        # 心跳进化器
        self.evolver: TemperEvolver = None
    
    def initialize(self) -> bool:
        """初始化系统"""
        print("🚀 初始化 Temper 系统...")
        
        # 1. 初始化配置系统
        self.config = ConfigManager()
        result = self.config.load()
        if not is_ok(result):
            print(f"❌ 配置加载失败: {result}")
            return False
        print("✅ 配置系统初始化完成")
        
        config = self.config.get()
        
        # 2. 初始化审计系统
        self.audit = AuditLogger(
            storage_dir=config.audit.storage_dir,
            max_file_size_mb=config.audit.max_file_size_mb
        )
        self.tracer = OperationTracer(self.audit)
        print("✅ 审计系统初始化完成")
        
        # 3. 初始化快照系统
        self.snapshots = SnapshotManager(
            storage_dir=f"{config.persistence.storage_dir}/snapshots"
        )
        print("✅ 快照系统初始化完成")
        
        # 4. 初始化自感知模块
        if config.self_awareness.enabled:
            self.metrics = MetricsCollector()
            self.monitor = ResourceMonitor(self.metrics)
            self.diagnostics = Diagnostics()
            
            # 注册资源健康检查
            self.diagnostics.register_check(
                "resources",
                self._create_resource_health_check()
            )
            
            self.metrics.start_collection(
                config.self_awareness.metrics_collection_interval
            )
            print("✅ 自感知模块初始化完成")
        
        # 5. 初始化自适应模块
        if config.self_adaptive.enabled:
            self.tuner = ParameterTuner(self.metrics)
            self.strategy_engine = StrategyEngine(self.metrics, self.tuner)
            print("✅ 自适应模块初始化完成")
        
        # 6. 初始化自组织模块
        if config.self_organizing.enabled:
            scheduler = TaskScheduler(config.self_organizing.max_concurrent_tasks)
            self.workflow_engine = WorkflowEngine(scheduler)
            print("✅ 自组织模块初始化完成")
        
        # 7. 初始化自编译模块
        if config.self_compiling.enabled:
            self.code_repair = CodeRepair(self.audit)
            self.code_generator = CodeGenerator(
                config.self_compiling.generation.get('template_dir', 'templates')
            )
            self.code_generator.install_builtin_templates()
            print("✅ 自编译模块初始化完成")
        
        # 8. 初始化心跳进化器
        evolver_config = EvolverConfig(
            self_check_interval=60,  # 每分钟自检
            adapt_interval=300,  # 每5分钟自适应
            repair_check_interval=3600,  # 每小时修复检查
            auto_repair_enabled=False,  # 安全优先，自动修复关闭
            debug=False
        )
        self.evolver = TemperEvolver(self, evolver_config)
        print("✅ 心跳进化器初始化完成")
        
        # 9. 启动事件总线
        event_bus.start()
        print("✅ 事件总线启动完成")
        
        # 9. 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 10. 恢复状态
        self._restore_state()
        
        # 记录启动事件
        self.audit.info(
            category=AuditCategory.SYSTEM,
            action="system.start",
            source="TemperSystem",
            parameters={'version': '3.0.0'}
        )
        
        print("\n🧊 Temper 系统初始化完成！")
        return True
    
    def _create_resource_health_check(self):
        """创建资源健康检查函数"""
        def check():
            summary = self.monitor.get_resource_summary()
            
            cpu = summary.get('cpu_percent', 0)
            memory = summary.get('memory', {}).get('percent', 0)
            disk = summary.get('disk', {}).get('percent', 0)
            
            thresholds = self.config.get().self_awareness.alert_thresholds
            
            issues = []
            if cpu >= thresholds.get('cpu_percent', 80):
                issues.append(f"CPU: {cpu:.1f}%")
            if memory >= thresholds.get('memory_percent', 85):
                issues.append(f"Memory: {memory:.1f}%")
            if disk >= thresholds.get('disk_percent', 90):
                issues.append(f"Disk: {disk:.1f}%")
            
            if issues:
                from temper.self_awareness.diagnostics import HealthCheck, HealthStatus
                return HealthCheck(
                    name="resources",
                    status=HealthStatus.DEGRADED,
                    message="; ".join(issues),
                    timestamp=datetime.now(),
                    details={'cpu': cpu, 'memory': memory, 'disk': disk}
                )
            
            from temper.self_awareness.diagnostics import HealthCheck, HealthStatus
            return HealthCheck(
                name="resources",
                status=HealthStatus.HEALTHY,
                message="All resources within normal limits",
                timestamp=datetime.now(),
                details={'cpu': cpu, 'memory': memory, 'disk': disk}
            )
        
        return check
    
    def _restore_state(self) -> None:
        """恢复系统状态"""
        # 从持久化存储恢复
        pass
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n🛑 收到终止信号，正在关闭...")
        self.shutdown()
        sys.exit(0)
    
    def run(self) -> None:
        """运行主循环"""
        self._running = True
        
        print("\n" + "=" * 50)
        print("🧊 Temper Evolve v3.0 - 四自系统")
        print("=" * 50)
        print()
        print("命令:")
        print("  /status    - 查看系统状态")
        print("  /metrics   - 查看系统指标")
        print("  /health    - 查看健康状态")
        print("  /config    - 查看/修改配置")
        print("  /snapshot  - 创建/恢复快照")
        print("  /audit     - 查看审计日志")
        print("  /repair    - 代码修复")
        print("  /generate  - 代码生成")
        print("  /evolver   - 心跳进化器控制")
        print("  /clear     - 清空对话历史")
        print("  exit       - 退出")
        print()
        
        while self._running:
            try:
                user_input = input("👤 你: ").strip()
                
                if user_input.lower() == 'exit':
                    break
                
                if user_input.lower() == '/status':
                    self._show_status()
                    continue
                
                if user_input.lower() == '/metrics':
                    self._show_metrics()
                    continue
                
                if user_input.lower() == '/health':
                    self._show_health()
                    continue
                
                if user_input.lower().startswith('/config'):
                    self._handle_config(user_input)
                    continue
                
                if user_input.lower().startswith('/snapshot'):
                    self._handle_snapshot(user_input)
                    continue
                
                if user_input.lower() == '/audit':
                    self._show_audit()
                    continue
                
                if user_input.lower() == '/repair':
                    self._handle_repair()
                    continue
                
                if user_input.lower() == '/generate':
                    self._handle_generate()
                    continue
                
                if user_input.lower().startswith('/evolver'):
                    self._handle_evolver(user_input)
                    continue
                
                if user_input:
                    self._process_input(user_input)
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        self.shutdown()
    
    def _show_status(self) -> None:
        """显示系统状态"""
        print("\n📊 系统状态:")
        print(f"  版本: 3.0.0")
        
        if self.diagnostics:
            status = self.diagnostics.get_overall_status()
            status_emoji = {
                'healthy': '🟢',
                'degraded': '🟡',
                'unhealthy': '🔴',
                'unknown': '⚪'
            }.get(status.value, '⚪')
            print(f"  健康状态: {status_emoji} {status.value}")
        
        if self.metrics:
            stats = self.metrics.get_stats()
            print(f"  指标收集器: {stats['collectors_count']} 个")
            print(f"  历史记录: {stats['history_size']} 条")
        
        if self.workflow_engine:
            stats = self.workflow_engine.get_stats()
            print(f"  工作流: {stats['workflows_count']} 个")
        
        print()
    
    def _show_metrics(self) -> None:
        """显示系统指标"""
        print("\n📈 系统指标:")
        if self.metrics:
            recent = self.metrics.get_history(limit=5)
            for m in recent:
                labels = ','.join(f"{k}={v}" for k, v in m.labels.items())
                label_str = f" [{labels}]" if labels else ""
                print(f"  {m.name}{label_str}: {m.value:.2f}{m.unit}")
        
        if self.monitor:
            summary = self.monitor.get_resource_summary()
            if 'error' not in summary:
                print(f"\n  资源摘要:")
                print(f"    CPU: {summary.get('cpu_percent', 0):.1f}%")
                mem = summary.get('memory', {})
                print(f"    内存: {mem.get('percent', 0):.1f}% ({mem.get('used_mb', 0):.0f} MB / {mem.get('total_mb', 0):.0f} MB)")
                disk = summary.get('disk', {})
                print(f"    磁盘: {disk.get('percent', 0):.1f}% ({disk.get('used_gb', 0):.1f} GB / {disk.get('total_gb', 0):.1f} GB)")
        print()
    
    def _show_health(self) -> None:
        """显示健康状态"""
        print("\n🏥 健康检查:")
        if self.diagnostics:
            report = self.diagnostics.get_health_report()
            print(f"  整体状态: {report['overall_status']}")
            print(f"  检查项: {report['summary']['total']} 个")
            print(f"    🟢 健康: {report['summary']['healthy']}")
            print(f"    🟡 降级: {report['summary']['degraded']}")
            print(f"    🔴 异常: {report['summary']['unhealthy']}")
            print(f"    ⚪ 未知: {report['summary']['unknown']}")
            
            for name, check in report['checks'].items():
                emoji = {'healthy': '🟢', 'degraded': '🟡', 'unhealthy': '🔴', 'unknown': '⚪'}.get(check['status'], '⚪')
                print(f"  {emoji} {name}: {check['message']}")
        print()
    
    def _handle_config(self, command: str) -> None:
        """处理配置命令"""
        parts = command.split()
        if len(parts) == 1:
            # 显示配置
            import json
            config_dict = self.config._config.to_dict()
            print("\n⚙️ 当前配置:")
            print(json.dumps(config_dict, indent=2, ensure_ascii=False))
        elif len(parts) >= 3:
            # 修改配置: /config path value
            path = parts[1]
            value = ' '.join(parts[2:])
            
            # 尝试解析值类型
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
            
            result = self.config.update(path, value)
            if is_ok(result):
                print(f"✅ 配置已更新: {path} = {value}")
            else:
                print(f"❌ 配置更新失败: {result}")
        print()
    
    def _handle_snapshot(self, command: str) -> None:
        """处理快照命令"""
        parts = command.split()
        
        if len(parts) == 1 or parts[1] == 'list':
            # 列出快照
            snapshots = self.snapshots.list_snapshots()
            print(f"\n📸 快照列表 ({len(snapshots)} 个):")
            for snap in snapshots[:10]:
                print(f"  {snap.id}: {snap.description or 'No description'} ({snap.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
        
        elif parts[1] == 'create':
            # 创建快照
            description = ' '.join(parts[2:]) if len(parts) > 2 else "Manual snapshot"
            import pickle
            state_data = pickle.dumps({'timestamp': datetime.now().isoformat()})
            snapshot = self.snapshots.create(state_data, description)
            print(f"✅ 快照已创建: {snapshot.id}")
        
        elif parts[1] == 'restore' and len(parts) > 2:
            # 恢复快照
            snapshot_id = parts[2]
            restored = self.snapshots.restore(snapshot_id)
            if restored:
                print(f"✅ 快照已恢复: {snapshot_id}")
            else:
                print(f"❌ 快照不存在: {snapshot_id}")
        
        elif parts[1] == 'delete' and len(parts) > 2:
            # 删除快照
            snapshot_id = parts[2]
            if self.snapshots.delete(snapshot_id):
                print(f"✅ 快照已删除: {snapshot_id}")
            else:
                print(f"❌ 快照不存在: {snapshot_id}")
        
        print()
    
    def _show_audit(self) -> None:
        """显示审计日志"""
        print("\n📝 最近审计日志:")
        records = self.audit.query(limit=10)
        for record in records:
            print(f"  [{record.timestamp.strftime('%H:%M:%S')}] {record.category.value}.{record.action} - {record.source}")
        print()
    
    def _handle_repair(self) -> None:
        """处理代码修复"""
        print("\n🔧 代码修复:")
        print("  功能开发中...")
        print()
    
    def _handle_generate(self) -> None:
        """处理代码生成"""
        print("\n📝 代码生成:")
        templates = self.code_generator.list_templates()
        print(f"  可用模板: {', '.join(templates)}")
        print()
    
    def _handle_evolver(self, command: str) -> None:
        """处理心跳进化器命令"""
        parts = command.split()
        
        if len(parts) == 1:
            # 显示状态
            print("\n🧊 心跳进化器状态:")
            if self.evolver:
                stats = self.evolver.get_stats()
                print(f"  运行中: {'✅ 是' if stats['running'] else '❌ 否'}")
                print(f"  运行时长: {stats['uptime_seconds']:.0f} 秒")
                print(f"  自检次数: {stats['self_checks']}")
                print(f"  自适应次数: {stats['adaptations']}")
                print(f"  修复扫描: {stats['repair_scans']}")
                print(f"  告警次数: {stats['alerts']}")
                print()
                print("  命令:")
                print("    /evolver start   - 启动进化器")
                print("    /evolver stop    - 停止进化器")
                print("    /evolver debug   - 切换调试模式")
            else:
                print("  ❌ 进化器未初始化")
        
        elif parts[1] == 'start':
            if self.evolver:
                self.evolver.start()
            else:
                print("❌ 进化器未初始化")
        
        elif parts[1] == 'stop':
            if self.evolver:
                self.evolver.stop()
            else:
                print("❌ 进化器未初始化")
        
        elif parts[1] == 'debug':
            if self.evolver:
                self.evolver.config.debug = not self.evolver.config.debug
                print(f"🔧 调试模式: {'开启' if self.evolver.config.debug else '关闭'}")
            else:
                print("❌ 进化器未初始化")
        
        print()
    
    def _process_input(self, user_input: str) -> None:
        """处理用户输入"""
        # 使用 tracer 追踪操作
        with self.tracer.trace(
            category=AuditCategory.USER_ACTION,
            action="chat",
            source="TemperSystem",
            parameters={'input': user_input[:100]}
        ):
            # 调用 AI 处理
            print(f"🤖 处理中: {user_input[:50]}...")
            print("  (AI 处理功能需要接入实际的 AI 服务)")
    
    def shutdown(self) -> None:
        """关闭系统"""
        print("\n🛑 正在关闭系统...")
        
        # 停止心跳进化器
        if self.evolver:
            self.evolver.stop()
        
        # 保存状态
        if self.snapshots:
            import pickle
            state_data = pickle.dumps({'shutdown': datetime.now().isoformat()})
            self.snapshots.create(state_data, "Shutdown snapshot")
        
        # 停止模块
        if self.metrics:
            self.metrics.stop_collection()
        
        if self.diagnostics:
            self.diagnostics.stop_auto_check()
        
        # 停止事件总线
        event_bus.stop()
        
        # 关闭审计日志
        if self.audit:
            self.audit.info(
                category=AuditCategory.SYSTEM,
                action="system.stop",
                source="TemperSystem"
            )
            self.audit.close()
        
        print("👋 系统已安全关闭")


def main():
    """主入口"""
    system = TemperSystem()
    
    if not system.initialize():
        print("❌ 系统初始化失败")
        sys.exit(1)
    
    system.run()


if __name__ == "__main__":
    from datetime import datetime
    main()
