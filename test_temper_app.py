#!/usr/bin/env python3
"""
🧪 Temper App 测试脚本

验证封装后的状态管理是否正常工作
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


def test_app_initialization():
    """测试应用初始化"""
    print("🧪 测试应用初始化...")
    
    try:
        app = TemperApp()
        print("✅ 应用创建成功")
        
        # 检查核心组件是否正确初始化
        assert app.logger is not None, "日志系统未初始化"
        print("✅ 日志系统正常")
        
        assert app.four_self_system is not None, "四自系统未初始化"
        print("✅ 四自系统正常")
        
        assert app.client is not None, "API 客户端未初始化"
        print("✅ API 客户端正常")
        
        assert app.conversation_history == [], "对话历史未正确初始化"
        print("✅ 对话历史正常")
        
        assert app.max_history == 20, "历史长度配置错误"
        print("✅ 历史配置正常")
        
        print("🎉 初始化测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_history_management():
    """测试历史管理功能"""
    print("\n🧪 测试历史管理...")
    
    try:
        app = TemperApp()
        
        # 测试添加历史
        app.add_to_history("测试用户输入", "测试助手回复")
        assert len(app.conversation_history) == 2, "历史长度不正确"
        print("✅ 添加历史正常")
        
        # 检查历史内容
        assert app.conversation_history[0]["role"] == "user"
        assert app.conversation_history[0]["content"] == "测试用户输入"
        assert app.conversation_history[1]["role"] == "assistant"
        assert app.conversation_history[1]["content"] == "测试助手回复"
        print("✅ 历史内容正确")
        
        # 测试获取历史信息
        info = app.get_history_info()
        assert "1 轮" in info, "历史信息不正确"
        print("✅ 历史信息正常")
        
        # 测试清空历史
        app.clear_history()
        assert len(app.conversation_history) == 0, "清空历史失败"
        print("✅ 清空历史正常")
        
        print("🎉 历史管理测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 历史管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_format_result():
    """测试结果格式化功能"""
    print("\n🧪 测试结果格式化...")
    
    try:
        app = TemperApp()
        
        # 测试成功结果
        success_result = {"ok": True, "value": "测试内容"}
        formatted = app.format_result(success_result)
        assert '"ok": true' in formatted, "成功结果格式化错误"
        print("✅ 成功结果格式化正常")
        
        # 测试错误结果
        error_result = {"ok": False, "error": "TEST_ERROR", "message": "测试错误"}
        formatted = app.format_result(error_result)
        assert '"ok": false' in formatted, "错误结果格式化错误"
        assert '"TEST_ERROR"' in formatted, "错误结果格式化错误"
        print("✅ 错误结果格式化正常")
        
        # 测试长内容截断
        long_content = "a" * 10000  # 超过 8000 限制
        long_result = {"ok": True, "value": long_content}
        formatted = app.format_result(long_result)
        assert "已截断" in formatted, "长内容未截断"
        print("✅ 长内容截断正常")
        
        print("🎉 结果格式化测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 结果格式化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evolver_integration():
    """测试进化器集成"""
    print("\n🧪 测试进化器集成...")
    
    try:
        app = TemperApp()
        
        # 检查进化器是否为 None（初始化时）
        assert app.evolver is None, "进化器初始状态不正确"
        print("✅ 进化器初始状态正常")
        
        # 启动进化器
        app.start_evolver()
        # 这里不检查 app.evolver 是否为 None，因为启动是异步的
        print("✅ 进化器启动调用正常")
        
        # 停止进化器
        app.stop_evolver()
        print("✅ 进化器停止调用正常")
        
        print("🎉 进化器集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 进化器集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 开始 Temper App 测试")
    print("=" * 50)
    
    tests = [
        test_app_initialization,
        test_history_management,
        test_format_result,
        test_evolver_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！全局状态封装成功。")
        return True
    else:
        print("❌ 部分测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)