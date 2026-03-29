# 读取文件
with open('temper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除错误添加的 except 块
wrong_except = '''    except Exception as e:
        log_exception(e, "chat 函数执行失败")
        print(f"❌ 对话处理失败: {e}")

    # 保存到对话历史'''

right_except = '''    except Exception as e:
        log_exception(e, "chat 函数执行失败")
        print(f"❌ 对话处理失败: {e}")
        return

    # 保存到对话历史'''

if wrong_except in content:
    content = content.replace(wrong_except, right_except)
    with open('temper.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Pattern not found')