# 读取文件
with open('temper.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修改的位置
# 在 "# 保存到对话历史（合并所有响应）" 之前添加 except 块
new_lines = []
for i, line in enumerate(lines):
    if '# 保存到对话历史（合并所有响应）' in line and i > 0:
        # 在这一行之前添加 except
        indent = '    '
        new_lines.append(indent + 'except Exception as e:\n')
        new_lines.append(indent + '    log_exception(e, "chat 函数执行失败")\n')
        new_lines.append(indent + '    print(f"❌ 对话处理失败: {e}")\n')
        new_lines.append('\n')
    new_lines.append(line)

# 写回文件
with open('temper.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Fixed!')