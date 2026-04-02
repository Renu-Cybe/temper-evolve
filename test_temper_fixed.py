#!/usr/bin/env python3
"""
🧪 Temper App 测试脚本 (完全修复版)
"""

import sys
import os
# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 从 temper.py 文件导入 TemperApp 类
import importlib.util
spec = importlib.util.spec_from_file_location("temper", "temper.py")
temper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(temper_module)
TemperApp = temper_module.TemperApp


def safe_print(*args, **kwargs):
    """安全打印，避免在某些环境下出错"""
    try:
        print(*args, **kwargs)
    except:
        # 如果打印失败，静默处理
        pass


def test_basic_functionality():
    """测试基本功能"""
    safe_print("Testing TemperApp initialization...")
    
    try:
        app = TemperApp()
        safe_print("PASS: Application created successfully")
        
        # 检查核心组件
        if app.logger is not None:
            safe_print("PASS: Logger initialized")
        else:
            safe_print("FAIL: Logger not initialized")
            return False
            
        if app.four_self_system is not None:
            safe_print("PASS: Four-self system initialized")
        else:
            safe_print("FAIL: Four-self system not initialized")
            return False
            
        if app.client is not None:
            safe_print("PASS: API client initialized")
        else:
            safe_print("FAIL: API client not initialized")
            return False
            
        if isinstance(app.conversation_history, list):
            safe_print("PASS: Conversation history initialized")
        else:
            safe_print("FAIL: Conversation history not properly initialized")
            return False
            
        safe_print("SUCCESS: Basic functionality test passed!")
        return True
        
    except Exception as e:
        safe_print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_history_management():
    """测试历史管理"""
    safe_print("\nTesting history management...")
    
    try:
        app = TemperApp()
        
        # 测试添加历史
        original_len = len(app.conversation_history)
        app.add_to_history("test input", "test response")
        if len(app.conversation_history) == original_len + 2:
            safe_print("PASS: History added correctly")
        else:
            safe_print(f"FAIL: History length incorrect: {len(app.conversation_history)}")
            return False
            
        # 测试清空历史
        app.clear_history()
        if len(app.conversation_history) == 0:
            safe_print("PASS: History cleared correctly")
        else:
            safe_print(f"FAIL: History not cleared: {len(app.conversation_history)}")
            return False
            
        safe_print("SUCCESS: History management test passed!")
        return True
        
    except Exception as e:
        safe_print(f"ERROR: History test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    safe_print("Starting Temper App Tests")
    safe_print("=" * 40)
    
    tests = [
        test_basic_functionality,
        test_history_management,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    safe_print("\n" + "=" * 40)
    safe_print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        safe_print("SUCCESS: All tests passed! Global state encapsulation successful.")
        return True
    else:
        safe_print("FAILURE: Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)