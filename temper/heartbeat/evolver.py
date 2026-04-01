#!/usr/bin/env python3
"""
🧊 Temper Evolver - 心跳进化器

让四自系统真正运转起来
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

# 核心组件
from temper.core.result import ok, err, is_ok, unwrap
from temper.core.events import event_bus, Event, EventType

# 审计
from temper.audit.logger import AuditLogger, AuditCategory, AuditLevel


@dataclass
class EvolverConfig:
    """心跳进化器配置"""
    
    # 自感知（Self-Awareness）
    self_check_interval: int = 60  # 秒，每分钟自检
    health_report_interval: int = 300  # 秒，每5分钟健康报告
    
    # 自适应（Self-Adaptive）
    adapt_interval: int = 300  # 秒，每5分钟自适应
    adapt_threshold: float = 0.1  # 变化阈值（10%变化才调整）
    
    # 自组织（Self-Organizing）
    workflow_check_interval: int = 60  # 秒，每分钟检查工作流
    
    # 自编译（Self-Compiling）
    repair_check_interval: int = 3600  # 秒，每小时检查修复
    auto_repair_enabled: bool = False  # 自动修复默认关闭（安全考虑）
    
    # 全局控制
    enabled: bool = True
    debug: bool = False


class TemperEvolver:
    """Temper 自动进化器
    
    核心职责：
    1. 定时触发自感知 → 健康检查、资源监控
    2. 定时触发自适应 → 参数调优、策略调整
    3. 定时触发自组织 → 工作流执行、任务编排
    4. 定时触发自编译 → 代码扫描、自修复
    
    使用示例：
        from temper import TemperSystem
        from temper.heartbeat import TemperEvolver, EvolverConfig
        
        system = TemperSystem()
        system.initialize()
        
        # 创建进化器
        config = EvolverConfig(
            self_check_interval=60,
            adapt_interval=300,
            auto_repair_enabled=False  # 安全优先
        )
        evolver = TemperEvolver(system, config)
        
        # 启动进化循环
        evolver.start()
        
        # 停止
        evolver.stop()
    """
    
    def __init__(self, system, config: Optional[EvolverConfig] = None):
        """
        初始化进化器
        
        Args:
            system: TemperSystem 实例
            config: 进化器配置（可选，使用默认配置）
        """
        self.system = system
        self.config = config or EvolverConfig()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 统计
        self._stats = {
            'self_checks': 0,
            'health_reports': 0,
            'adaptations': 0,
            'repair_scans': 0,
            'repairs': 0,
            'alerts': 0,
            'start_time': None,
            'last_check_time': None,
            'last_adapt_time': None,
            'last_repair_time': None,
        }
    
    def start(self) -> None:
        """启动进化循环"""
        if self._running:
            print("⚠️ 进化器已在运行")
            return
        
        self._running = True
        self._stats['start_time'] = datetime.now()
        
        # 创建后台线程运行异步循环
        self._thread = threading.Thread(
            target=self._run_async_loop,
            daemon=True,
            name="TemperEvolver"
        )
        self._thread.start()
        
        # 记录审计日志
        if self.system.audit:
            self.system.audit.info(
                category=AuditCategory.SYSTEM,
                action="evolver.start",
                source="TemperEvolver",
                parameters={
                    'config': {
                        'self_check_interval': self.config.self_check_interval,
                        'adapt_interval': self.config.adapt_interval,
                        'repair_check_interval': self.config.repair_check_interval,
                    }
                }
            )
        
        print("🧊 Temper 进化器已启动")
        print(f"  ⏱️ 自检间隔: {self.config.self_check_interval}秒")
        print(f"  ⏱️ 自适应间隔: {self.config.adapt_interval}秒")
        print(f"  ⏱️ 修复检查间隔: {self.config.repair_check_interval}秒")
    
    def stop(self) -> None:
        """停止进化循环"""
        if not self._running:
            return
        
        self._running = False
        
        # 记录审计日志
        if self.system.audit:
            duration = (datetime.now() - self._stats['start_time']).total_seconds()
            self.system.audit.info(
                category=AuditCategory.SYSTEM,
                action="evolver.stop",
                source="TemperEvolver",
                parameters={
                    'stats': self._stats,
                    'duration_seconds': duration
                }
            )
        
        print("🛑 Temper 进化器已停止")
        print(f"  📊 运行统计:")
        print(f"    自检次数: {self._stats['self_checks']}")
        print(f"    自适应次数: {self._stats['adaptations']}")
        print(f"    修复扫描: {self._stats['repair_scans']}")
        print(f"    告警次数: {self._stats['alerts']}")
    
    def _run_async_loop(self) -> None:
        """在后台线程中运行异步循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._evolution_loop())
        except Exception as e:
            print(f"❌ 进化循环异常: {e}")
            if self.system.audit:
                self.system.audit.error(
                    category=AuditCategory.SYSTEM,
                    action="evolver.error",
                    source="TemperEvolver",
                    parameters={'error': str(e)}
                )
        finally:
            self._loop.close()
    
    async def _evolution_loop(self) -> None:
        """主进化循环"""
        print("🔄 进化循环开始...")
        
        while self._running:
            now = datetime.now()
            
            # 1. 自感知：每 self_check_interval 秒执行
            if self._should_run('last_check_time', self.config.self_check_interval):
                await self._self_check()
                self._stats['last_check_time'] = now
            
            # 2. 自适应：每 adapt_interval 秒执行
            if self._should_run('last_adapt_time', self.config.adapt_interval):
                await self._adapt()
                self._stats['last_adapt_time'] = now
            
            # 3. 自编译：每 repair_check_interval 秒执行
            if self._should_run('last_repair_time', self.config.repair_check_interval):
                await self._repair_check()
                self._stats['last_repair_time'] = now
            
            # 等待下一个周期
            await asyncio.sleep(self.config.self_check_interval)
        
        print("🔄 进化循环结束")
    
    def _should_run(self, last_key: str, interval: int) -> bool:
        """判断是否应该运行某个任务"""
        last_time = self._stats.get(last_key)
        if not last_time:
            return True
        
        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed >= interval
    
    async def _self_check(self) -> None:
        """自感知：系统健康检查"""
        self._stats['self_checks'] += 1
        
        if self.config.debug:
            print(f"🔍 [{datetime.now().strftime('%H:%M:%S')}] 执行自检...")
        
        # 获取资源摘要
        if self.system.monitor:
            summary = self.system.monitor.get_resource_summary()
            
            # 检查资源阈值
            thresholds = self.system.config.get().self_awareness
            
            alerts = []
            
            # CPU 检查
            cpu = summary.get('cpu_percent', 0)
            if cpu >= thresholds.cpu_critical:
                alerts.append(f"🔴 CPU 严重: {cpu:.1f}%")
                self._stats['alerts'] += 1
            elif cpu >= thresholds.cpu_warning:
                alerts.append(f"🟡 CPU 警告: {cpu:.1f}%")
            
            # 内存检查
            mem = summary.get('memory', {})
            mem_percent = mem.get('percent', 0)
            if mem_percent >= thresholds.memory_critical:
                alerts.append(f"🔴 内存严重: {mem_percent:.1f}%")
                self._stats['alerts'] += 1
            elif mem_percent >= thresholds.memory_warning:
                alerts.append(f"🟡 内存警告: {mem_percent:.1f}%")
            
            # 磁盘检查
            disk = summary.get('disk', {})
            disk_percent = disk.get('percent', 0)
            if disk_percent >= thresholds.disk_critical:
                alerts.append(f"🔴 磁盘严重: {disk_percent:.1f}%")
                self._stats['alerts'] += 1
            elif disk_percent >= thresholds.disk_warning:
                alerts.append(f"🟡 磁盘警告: {disk_percent:.1f}%")
            
            # 有告警时输出
            if alerts:
                print(f"\n⚠️ 资源告警:")
                for alert in alerts:
                    print(f"  {alert}")
                
                # 发布事件
                event_bus.publish(Event(
                    type=EventType.ALERT_TRIGGERED,
                    source="TemperEvolver",
                    data={'alerts': alerts, 'summary': summary}
                ))
                
                # 记录审计
                if self.system.audit:
                    self.system.audit.warning(
                        category=AuditCategory.HEALTH,
                        action="resource.alert",
                        source="TemperEvolver",
                        parameters={'alerts': alerts}
                    )
            elif self.config.debug:
                print(f"  ✅ 资源正常: CPU {cpu:.1f}% | 内存 {mem_percent:.1f}% | 磁盘 {disk_percent:.1f}%")
        
        # 运行诊断检查
        if self.system.diagnostics:
            try:
                report = self.system.diagnostics.run_quick_check()
                if self.config.debug:
                    print(f"  ✅ 健康状态: {report['overall_status']}")
            except Exception as e:
                if self.config.debug:
                    print(f"  ❌ 诊断失败: {e}")
    
    async def _adapt(self) -> None:
        """自适应：参数调优"""
        self._stats['adaptations'] += 1
        
        if self.config.debug:
            print(f"🔧 [{datetime.now().strftime('%H:%M:%S')}] 执行自适应...")
        
        if self.system.tuner and self.system.metrics:
            # 获取历史指标
            history = self.system.metrics.get_history(hours=1)
            
            if history:
                # 分析并生成建议
                suggestions = self.system.tuner.analyze_trends(history)
                
                if suggestions:
                    print(f"\n🔄 自适应建议:")
                    for param, (current, suggested, reason) in suggestions.items():
                        change_pct = abs(suggested - current) / max(current, 1) * 100
                        
                        # 变化超过阈值才调整
                        if change_pct >= self.config.adapt_threshold * 100:
                            print(f"  {param}: {current} → {suggested} ({reason})")
                            
                            # 记录审计
                            if self.system.audit:
                                self.system.audit.info(
                                    category=AuditCategory.ADAPTATION,
                                    action="parameter.tune",
                                    source="TemperEvolver",
                                    parameters={
                                        'param': param,
                                        'from': current,
                                        'to': suggested,
                                        'reason': reason
                                    }
                                )
                elif self.config.debug:
                    print(f"  ✅ 无需调整")
    
    async def _repair_check(self) -> None:
        """自编译：代码修复检查"""
        self._stats['repair_scans'] += 1
        
        if self.config.debug:
            print(f"🔨 [{datetime.now().strftime('%H:%M:%S')}] 执行修复检查...")
        
        if self.system.code_repair:
            try:
                # 扫描代码问题
                issues = await self.system.code_repair.scan()
                
                if issues:
                    print(f"\n🔧 发现 {len(issues)} 个潜在问题:")
                    for issue in issues[:5]:  # 只显示前5个
                        print(f"  - {issue}")
                    
                    # 自动修复（如果启用）
                    if self.config.auto_repair_enabled:
                        for issue in issues:
                            result = await self.system.code_repair.fix(issue)
                            if is_ok(result):
                                self._stats['repairs'] += 1
                                print(f"  ✅ 已修复: {issue}")
                                
                                # 记录审计
                                if self.system.audit:
                                    self.system.audit.info(
                                        category=AuditCategory.REPAIR,
                                        action="code.fix",
                                        source="TemperEvolver",
                                        parameters={'issue': str(issue)}
                                    )
                    else:
                        print(f"  ⏳ 自动修复未启用，需要手动确认")
                elif self.config.debug:
                    print(f"  ✅ 无代码问题")
                    
            except Exception as e:
                if self.config.debug:
                    print(f"  ❌ 修复检查失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计"""
        return {
            'running': self._running,
            **self._stats,
            'uptime_seconds': (
                (datetime.now() - self._stats['start_time']).total_seconds()
                if self._stats['start_time'] else 0
            )
        }