#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试心跳进化器"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("心跳进化器测试")
print("=" * 60)

# 导入模块
try:
    from temper.heartbeat import TemperEvolver, EvolverConfig
    print("[OK] 心跳模块导入成功")
except Exception as e:
    print(f"[FAIL] 导入失败: {e}")
    sys.exit(1)

# 创建模拟系统
class MockSystem:
    def __init__(self):
        self.audit = None
        self.metrics = None
        self.monitor = None
        self.diagnostics = None
        self.tuner = None
        self.code_repair = None
        
        class MockConfig:
            class self_awareness:
                cpu_warning = 70.0
                cpu_critical = 90.0
                memory_warning = 80.0
                memory_critical = 95.0
                disk_warning = 85.0
                disk_critical = 95.0
        
        self.config = MockConfig()

print("[OK] 模拟系统创建成功")

# 创建进化器
config = EvolverConfig(
    self_check_interval=5,
    adapt_interval=10,
    repair_check_interval=30,
    auto_repair_enabled=False,
    debug=True
)
print(f"[OK] 配置创建成功: 自检间隔={config.self_check_interval}秒")

system = MockSystem()
evolver = TemperEvolver(system, config)
print("[OK] 进化器创建成功")

# 启动
evolver.start()
print("[OK] 进化器启动成功")

# 运行 15 秒
print("-" * 60)
print("运行 15 秒...")
time.sleep(15)

# 停止
print("-" * 60)
evolver.stop()
print("[OK] 进化器停止成功")

# 统计
stats = evolver.get_stats()
print(f"[OK] 统计: 自检={stats['self_checks']}次, 自适应={stats['adaptations']}次")

print("=" * 60)
print("测试完成")
print("=" * 60)