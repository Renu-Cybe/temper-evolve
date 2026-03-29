with open('temper.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 'except Exception as e:' 且在 'chat 函数执行失败' 之后的那一行
for i, line in enumerate(lines):
    if 'chat 函数执行失败' in line and i + 1 < len(lines):
        # 在下一行（print 语句）之后添加 return
        if 'print(f"❌ 对话处理失败' in lines[i + 1]:
            # 检查是否已经添加了 return
            if i + 2 >= len(lines) or 'return' not in lines[i + 2]:
                # 插入 return
                indent = '        '
                lines.insert(i + 2, indent + 'return\n')
                print(f'在第 {i + 3} 行插入了 return')
                break

with open('temper.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done!')