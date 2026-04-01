#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试心跳进化器

验证四自系统是否真正运转
"""

import sys
import os
import time
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temper.heartbeat import TemperEvolver, EvolverConfig


class MockSystem:
    """模拟 TemperSystem 用于测试"""
    
    def __init__(self):
        from temper.audit.logger import AuditLogger
        from temper.self_awareness.metrics import MetricsCollector
        from temper.self_awareness.resources import ResourceMonitor
        
        self.audit = AuditLogger(storage_dir="test_logs")
        self.metrics = MetricsCollector()
        self.monitor = ResourceMonitor(self.metrics)
        self.diagnostics = None
        self.tuner = None
        self.code_repair = None
        
        # 模拟 config
        class MockConfig:
            class self_awareness:
                cpu_warning = 70.0
                cpu_critical = 90.0
                memory_warning = 80.0
                memory_critical = 95.0
                disk_warning = 85.0
                disk_critical = 95.0
        
        self.config = MockConfig()
        
        # 启动指标收集
        self.metrics.start_collection(interval=5)


def test_evolver():
    """测试心跳进化器"""
    print("=" * 60)
    print("🧊 心跳进化器测试")
    print("=" * 60)
    print()
    
    # 创建模拟系统
    print("📦 初始化模拟系统...")
    system = MockSystem()
    print("✅ 模拟系统就绪")
    print()
    
    # 创建进化器配置（调试模式，快速测试）
    config = EvolverConfig(
        self_check_interval=10,  # 每10秒自检
        adapt_interval=30,  # 每30秒自适应
        repair_check_interval=60,  # 每60秒修复检查
        auto_repair_enabled=False,
        debug=True  # 开启调试输出
    )
    
    print("⚙️ 进化器配置:")
    print(f"  自检间隔: {config.self_check_interval}秒")
    print(f"  自适应间隔: {config.adapt_interval}秒")
    print(f"  调试模式: {'开启' if config.debug else '关闭'}")
    print()
    
    # 创建进化器
    evolver = TemperEvolver(system, config)
    
    # 启动
    print("🚀 启动进化器...")
    evolver.start()
    print()
    
    # 运行 60 秒
    print("⏱️ 运行 60 秒...")
    print("-" * 60)
    
    try:
        for i in range(60):
            time.sleep(1)
            
            # 每 10 秒显示统计
            if (i + 1) % 10 == 0:
                stats = evolver.get_stats()
                print(f"\n📊 [{i+1}秒] 统计:")
                print(f"  自检: {stats['self_checks']} 次")
                print(f"  自适应: {stats['adaptations']} 次")
                print(f"  告警: {stats['alerts']} 次")
                print()
    
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    
    # 停止
    print("-" * 60)
    print("\n🛑 停止进化器...")
    evolver.stop()
    
    # 最终统计
    stats = evolver.get_stats()
    print("\n📈 最终统计:")
    print(f"  运行时长: {stats['uptime_seconds']:.0f} 秒")
    print(f"  自检次数: {stats['self_checks']}")
    print(f"  自适应次数: {stats['adaptations']}")
    print(f"  告警次数: {stats['alerts']}")
    print()
    
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_evolver()