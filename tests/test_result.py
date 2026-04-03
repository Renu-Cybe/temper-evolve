#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Codong 风格错误处理系统

覆盖测试：
1. ok/err 创建
2. is_error/is_ok 检查
3. unwrap 提取值
4. unwrap_or_raise 抛出异常
5. 便捷错误函数
6. 函数式操作（map, bind, flat_map）
"""

import sys
sys.path.insert(0, '..')

from temper.core.result import (
    ok, err, is_error, is_ok, unwrap, unwrap_or_raise,
    map_result, bind_result, flat_map, try_catch,
    CodongError, ErrorCode,
    file_not_found, file_read_error, file_write_error,
    permission_denied, network_error, timeout_error,
    validation_error, not_found
)


def test_ok_creation():
    """测试成功结果创建"""
    result = ok(42)
    assert result['ok'] is True
    assert result['value'] == 42
    print("[OK] test_ok_creation")


def test_err_creation():
    """测试错误结果创建"""
    result = err("TEST_ERROR", "测试错误")
    assert result['ok'] is False
    assert result['error'] == "TEST_ERROR"
    assert result['message'] == "测试错误"
    print("[OK] test_err_creation")


def test_err_with_enum():
    """测试使用 ErrorCode 枚举创建错误"""
    result = err(ErrorCode.VALIDATION_ERROR, "验证失败")
    assert result['error'] == "validation_error"
    print("[OK] test_err_with_enum")


def test_err_with_details():
    """测试带详细信息的错误"""
    result = err("TEST_ERROR", "测试错误", {"field": "value"})
    assert result['details'] == {"field": "value"}
    print("[OK] test_err_with_details")


def test_is_error():
    """测试错误检查"""
    assert is_error(ok(42)) is False
    assert is_error(err("E", "m")) is True
    assert is_error({"ok": False}) is True
    assert is_error(None) is True  # 非 dict 视为错误
    print("[OK] test_is_error")


def test_is_ok():
    """测试成功检查"""
    assert is_ok(ok(42)) is True
    assert is_ok(err("E", "m")) is False
    assert is_ok(None) is False
    print("[OK] test_is_ok")


def test_unwrap_success():
    """测试提取成功值"""
    assert unwrap(ok(42)) == 42
    assert unwrap(ok({"key": "value"})) == {"key": "value"}
    print("[OK] test_unwrap_success")


def test_unwrap_error_with_default():
    """测试错误时返回默认值"""
    assert unwrap(err("E", "m")) is None
    assert unwrap(err("E", "m"), default=0) == 0
    assert unwrap(err("E", "m"), default="default") == "default"
    print("[OK] test_unwrap_error_with_default")


def test_unwrap_or_raise_success():
    """测试成功时提取值"""
    assert unwrap_or_raise(ok(42)) == 42
    print("[OK] test_unwrap_or_raise_success")


def test_unwrap_or_raise_error():
    """测试错误时抛出异常"""
    try:
        unwrap_or_raise(err("TEST_ERROR", "测试错误"))
        assert False, "应该抛出异常"
    except CodongError as e:
        assert e.error_code == "TEST_ERROR"
        assert "测试错误" in str(e)
    print("[OK] test_unwrap_or_raise_error")


def test_convenient_error_functions():
    """测试便捷错误函数"""
    # file_not_found
    result = file_not_found("/tmp/test.txt")
    assert result['error'] == "file_not_found"
    assert "/tmp/test.txt" in result['message']

    # network_error
    result = network_error("https://example.com", "连接拒绝")
    assert result['error'] == "network_error"

    # timeout_error
    result = timeout_error("API 调用", 30.0)
    assert result['error'] == "timeout"
    assert "30.0" in result['message']

    # validation_error
    result = validation_error("name", "不能为空")
    assert result['error'] == "validation_error"

    # not_found
    result = not_found("User", "123")
    assert result['error'] == "not_found"

    print("[OK] test_convenient_error_functions")


def test_map_result_success():
    """测试成功结果的映射"""
    result = ok(5)
    mapped = map_result(result, lambda x: x * 2)
    assert mapped['ok'] is True
    assert mapped['value'] == 10
    print("[OK] test_map_result_success")


def test_map_result_error():
    """测试错误结果的映射（保持不变）"""
    result = err("E", "m")
    mapped = map_result(result, lambda x: x * 2)
    assert mapped['ok'] is False
    assert mapped['error'] == "E"
    print("[OK] test_map_result_error")


def test_bind_result_chain():
    """测试链式绑定"""
    result = ok(5)
    result = bind_result(result, lambda x: ok(x * 2))
    result = bind_result(result, lambda x: ok(x + 1))
    assert result['value'] == 11
    print("[OK] test_bind_result_chain")


def test_bind_result_error_propagation():
    """测试错误传播"""
    result = ok(5)
    result = bind_result(result, lambda x: err("FIRST_ERROR", "第一步错误"))
    result = bind_result(result, lambda x: ok(x * 2))
    assert result['ok'] is False
    assert result['error'] == "FIRST_ERROR"
    print("[OK] test_bind_result_error_propagation")


def test_flat_map():
    """测试 flat_map（bind 的别名）"""
    result = ok(10)
    result = flat_map(result, lambda x: ok(x / 2))
    assert result['value'] == 5.0
    print("[OK] test_flat_map")


def test_try_catch_success():
    """测试 try_catch 成功"""
    result = try_catch(lambda: 10 / 2)
    assert result['ok'] is True
    assert result['value'] == 5.0
    print("[OK] test_try_catch_success")


def test_try_catch_exception():
    """测试 try_catch 捕获异常"""
    result = try_catch(lambda: 10 / 0, "DIVISION_ERROR")
    assert result['ok'] is False
    assert result['error'] == "DIVISION_ERROR"
    print("[OK] test_try_catch_exception")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Phase 1: Codong 错误处理系统测试")
    print("=" * 60)

    tests = [
        test_ok_creation,
        test_err_creation,
        test_err_with_enum,
        test_err_with_details,
        test_is_error,
        test_is_ok,
        test_unwrap_success,
        test_unwrap_error_with_default,
        test_unwrap_or_raise_success,
        test_unwrap_or_raise_error,
        test_convenient_error_functions,
        test_map_result_success,
        test_map_result_error,
        test_bind_result_chain,
        test_bind_result_error_propagation,
        test_flat_map,
        test_try_catch_success,
        test_try_catch_exception,
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
