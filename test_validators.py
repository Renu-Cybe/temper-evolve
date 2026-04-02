#!/usr/bin/env python3
"""测试安全检查层"""

import sys
sys.path.insert(0, '.')

from temper.validators import validate_command, validate_evolver_config, TemperError

def test_dangerous_command():
    """测试 1: 危险命令检测"""
    try:
        validate_command('rm -rf /')
        print('[FAIL] Test 1: should detect dangerous command')
    except Exception as e:
        print('[PASS] Test 1: dangerous command detected')
        print(f'  Error: {e.code} - {e.message}')
        print(f'  Suggestion: {e.suggestion}')

def test_invalid_config():
    """测试 2: 配置验证"""
    result = validate_evolver_config({'self_check_interval': 5})
    if not result.get('ok'):
        print('[PASS] Test 2: config range validation')
        print(f'  Error: {result["error"]}')
        print(f'  Suggestion: {result["suggestion"]}')
    else:
        print('[FAIL] Test 2: should detect invalid config value')

def test_valid_config():
    """测试 3: 正常配置"""
    result = validate_evolver_config({
        'self_check_interval': 60,
        'adapt_interval': 300,
        'repair_check_interval': 3600
    })
    if result.get('ok'):
        print('[PASS] Test 3: valid config accepted')
    else:
        print('[FAIL] Test 3: valid config should pass')

if __name__ == '__main__':
    print('[TEST] Security Validators\n')
    test_dangerous_command()
    print()
    test_invalid_config()
    print()
    test_valid_config()
    print()
    print('[PASS] All tests completed!')