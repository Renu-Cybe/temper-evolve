#!/usr/bin/env python3
"""
🧪 Temper App 测试脚本 (简化版)
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


def test_basic_functionality():
    """测试基本功能"""
    print("Testing TemperApp initialization...")
    
    try:
        app = TemperApp()
        print("PASS: Application created successfully")
        
        # 检查核心组件
        if app.logger is not None:
            print("PASS: Logger initialized")
        else:
            print("FAIL: Logger not initialized")
            return False
            
        if app.four_self_system is not None:
            print("PASS: Four-self system initialized")
        else:
            print("FAIL: Four-self system not initialized")
            return False
            
        if app.client is not None:
            print("PASS: API client initialized")
        else:
            print("FAIL: API client not initialized")
            return False
            
        if isinstance(app.conversation_history, list):
            print("PASS: Conversation history initialized")
        else:
            print("FAIL: Conversation history not properly initialized")
            return False
            
        print("SUCCESS: Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_history_management():
    """测试历史管理"""
    print("\nTesting history management...")
    
    try:
        app = TemperApp()
        
        # 测试添加历史
        app.add_to_history("test input", "test response")
        if len(app.conversation_history) == 2:
            print("PASS: History added correctly")
        else:
            print(f"FAIL: History length incorrect: {len(app.conversation_history)}")
            return False
            
        # 测试清空历史
        app.clear_history()
        if len(app.conversation_history) == 0:
            print("PASS: History cleared correctly")
        else:
            print(f"FAIL: History not cleared: {len(app.conversation_history)}")
            return False
            
        print("SUCCESS: History management test passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: History test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("Starting Temper App Tests")
    print("=" * 40)
    
    tests = [
        test_basic_functionality,
        test_history_management,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("SUCCESS: All tests passed! Global state encapsulation successful.")
        return True
    else:
        print("FAILURE: Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)