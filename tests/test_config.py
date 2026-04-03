#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置系统

覆盖测试：
1. Config schema 创建
2. HeartbeatConfig 配置
3. 配置转换
4. 配置验证
"""

import sys
sys.path.insert(0, '..')

from temper.config.schema import (
    Config,
    HeartbeatConfig,
    SystemConfig,
    SelfAwarenessConfig,
    SelfAdaptiveConfig,
    SelfOrganizingConfig,
    SelfCompilingConfig,
    AuditConfig,
    PersistenceConfig,
)
from temper.heartbeat.evolver import EvolverConfig


# ==================== HeartbeatConfig 测试 ====================

def test_heartbeat_config_defaults():
    """测试 HeartbeatConfig 默认值"""
    config = HeartbeatConfig()

    assert config.enabled is True
    assert config.debug is False
    assert config.self_check_interval == 60
    assert config.health_report_interval == 300
    assert config.adapt_interval == 300
    assert config.adapt_threshold == 0.1
    assert config.workflow_check_interval == 60
    assert config.repair_check_interval == 3600
    assert config.auto_repair_enabled is False

    print("[OK] test_heartbeat_config_defaults")


def test_heartbeat_config_custom():
    """测试自定义 HeartbeatConfig"""
    config = HeartbeatConfig(
        enabled=False,
        debug=True,
        self_check_interval=30,
        adapt_interval=600,
    )

    assert config.enabled is False
    assert config.debug is True
    assert config.self_check_interval == 30
    assert config.adapt_interval == 600

    print("[OK] test_heartbeat_config_custom")


# ==================== EvolverConfig 转换测试 ====================

def test_evolver_config_from_heartbeat():
    """测试从 HeartbeatConfig 创建 EvolverConfig"""
    heartbeat = HeartbeatConfig(
        self_check_interval=90,
        adapt_interval=450,
        auto_repair_enabled=True,
        debug=True
    )

    evolver = EvolverConfig.from_heartbeat_config(heartbeat)

    assert evolver.self_check_interval == 90
    assert evolver.adapt_interval == 450
    assert evolver.auto_repair_enabled is True
    assert evolver.debug is True

    print("[OK] test_evolver_config_from_heartbeat")


def test_evolver_config_to_dict():
    """测试 EvolverConfig 转字典"""
    evolver = EvolverConfig(
        self_check_interval=120,
        adapt_interval=600,
        repair_check_interval=7200,
    )

    config_dict = evolver.to_heartbeat_config()

    assert isinstance(config_dict, dict)
    assert config_dict['self_check_interval'] == 120
    assert config_dict['adapt_interval'] == 600
    assert config_dict['repair_check_interval'] == 7200
    assert config_dict['enabled'] is True
    assert config_dict['debug'] is False

    print("[OK] test_evolver_config_to_dict")


def test_evolver_config_roundtrip():
    """测试配置往返转换"""
    original = HeartbeatConfig(
        self_check_interval=180,
        adapt_interval=900,
        auto_repair_enabled=True,
    )

    # HeartbeatConfig -> EvolverConfig -> dict
    evolver = EvolverConfig.from_heartbeat_config(original)
    config_dict = evolver.to_heartbeat_config()

    # 验证关键字段
    assert config_dict['self_check_interval'] == 180
    assert config_dict['adapt_interval'] == 900
    assert config_dict['auto_repair_enabled'] is True

    print("[OK] test_evolver_config_roundtrip")


# ==================== 完整 Config 测试 ====================

def test_full_config_with_heartbeat():
    """测试完整 Config 包含 heartbeat 字段"""
    config = Config()

    assert hasattr(config, 'heartbeat')
    assert isinstance(config.heartbeat, HeartbeatConfig)
    assert config.heartbeat.enabled is True

    print("[OK] test_full_config_with_heartbeat")


def test_full_config_to_dict():
    """测试完整 Config 转字典"""
    config = Config()
    config_dict = config.to_dict()

    assert isinstance(config_dict, dict)
    assert 'heartbeat' in config_dict
    assert config_dict['heartbeat']['enabled'] is True

    print("[OK] test_full_config_to_dict")


def test_full_config_from_dict():
    """测试从字典创建完整 Config"""
    data = {
        'system': {'name': 'test-system', 'version': '1.0.0'},
        'heartbeat': {
            'enabled': False,
            'debug': True,
            'self_check_interval': 30,
        },
        'self_awareness': {'enabled': True},
    }

    config = Config.from_dict(data)

    assert config.system.name == 'test-system'
    assert config.heartbeat.enabled is False
    assert config.heartbeat.debug is True
    assert config.heartbeat.self_check_interval == 30

    print("[OK] test_full_config_from_dict")


# ==================== 其他配置测试 ====================

def test_system_config():
    """测试 SystemConfig"""
    config = SystemConfig()
    assert config.name == "temper"
    assert config.version == "3.0.0"
    assert config.debug_mode is False
    print("[OK] test_system_config")


def test_self_awareness_config():
    """测试 SelfAwarenessConfig"""
    config = SelfAwarenessConfig()
    assert config.enabled is True
    assert config.health_check_interval == 30
    assert config.alert_thresholds['cpu_percent'] == 80.0
    print("[OK] test_self_awareness_config")


def test_persistence_config():
    """测试 PersistenceConfig"""
    config = PersistenceConfig()
    assert config.enabled is True
    assert config.auto_save_interval == 60
    assert config.compression_enabled is True
    print("[OK] test_persistence_config")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 4: 配置系统测试")
    print("=" * 60)

    tests = [
        test_heartbeat_config_defaults,
        test_heartbeat_config_custom,
        test_evolver_config_from_heartbeat,
        test_evolver_config_to_dict,
        test_evolver_config_roundtrip,
        test_full_config_with_heartbeat,
        test_full_config_to_dict,
        test_full_config_from_dict,
        test_system_config,
        test_self_awareness_config,
        test_persistence_config,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: 异常 - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
