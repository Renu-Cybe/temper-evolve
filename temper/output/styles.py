#!/usr/bin/env python3
"""
Output Styles - 输出格式系统

基于 Claude Code 的 Output Styles 设计：
- Default: 标准软件工程模式
- Explanatory: 教育模式（提供 Insights）
- Learning: 学习模式（交互式编程）

支持自定义样式：Markdown + frontmatter
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import os


class OutputStyle(Enum):
    """输出样式枚举"""
    DEFAULT = "default"
    EXPLANATORY = "explanatory"
    LEARNING = "learning"
    CUSTOM = "custom"


@dataclass
class OutputFormat:
    """输出格式定义"""
    style: OutputStyle = OutputStyle.DEFAULT
    structured: bool = False  # 是否强制结构化输出
    schema: Optional[Dict[str, Any]] = None  # JSON Schema
    keep_coding_instructions: bool = True
    
    # 输出配置
    max_length: Optional[int] = None
    include_metadata: bool = False
    include_suggestions: bool = True
    
    # 自定义指令
    custom_instructions: str = ""


class OutputStyleManager:
    """
    输出样式管理器
    
    使用示例:
        manager = OutputStyleManager()
        
        # 设置输出样式
        manager.set_style(OutputStyle.EXPLANATORY)
        
        # 设置结构化输出
        manager.set_structured_output({
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "issues": {"type": "array"}
            }
        })
        
        # 格式化输出
        result = manager.format_output({
            "status": "healthy",
            "issues": []
        })
        
        # 创建自定义样式
        manager.create_custom_style("my_style", instructions="...")
    """
    
    # 预定义样式
    BUILTIN_STYLES = {
        OutputStyle.DEFAULT: {
            'name': 'Default',
            'description': '标准软件工程模式，高效完成任务',
            'keep_coding_instructions': True,
            'instructions': '''
# Default Output Style

You are an interactive CLI tool that helps users with software engineering tasks.

## Core Behaviors
- Be concise and direct
- Focus on completing tasks efficiently
- Provide actionable suggestions
- Verify code with tests when possible
'''
        },
        OutputStyle.EXPLANATORY: {
            'name': 'Explanatory',
            'description': '教育模式，提供 Insights 解释实现选择',
            'keep_coding_instructions': True,
            'instructions': '''
# Explanatory Output Style

You are an interactive CLI tool that helps users learn while completing tasks.

## Core Behaviors
- Provide "Insights" sections explaining implementation choices
- Help users understand codebase patterns
- Explain why certain approaches are preferred
- Balance task completion with education

## Insight Format
```
💡 Insight: [Topic]
[Explanation of why this approach was chosen]
[Alternative approaches considered]
```
'''
        },
        OutputStyle.LEARNING: {
            'name': 'Learning',
            'description': '学习模式，交互式编程，添加 TODO(human) 标记',
            'keep_coding_instructions': True,
            'instructions': '''
# Learning Output Style

You are an interactive CLI tool that helps users learn by doing.

## Core Behaviors
- Ask users to contribute small, strategic pieces of code
- Add `TODO(human)` markers for user implementation
- Provide guidance, not just solutions
- Encourage experimentation

## TODO(human) Format
```python
# TODO(human): Implement this function
def your_function():
    # Hint: Consider using...
    pass
```
'''
        }
    }
    
    def __init__(self, config_path: str = None):
        """
        初始化输出样式管理器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        self.config_path = config_path or "temper/.claude/settings.local.json"
        self.current_style = OutputStyle.DEFAULT
        self.custom_styles: Dict[str, dict] = {}
        self.output_format = OutputFormat()
        
        # 加载配置
        self._load_config()
    
    def set_style(self, style: OutputStyle) -> bool:
        """
        设置输出样式
        
        Args:
            style: 输出样式
        
        Returns:
            是否设置成功
        """
        if style not in self.BUILTIN_STYLES and style != OutputStyle.CUSTOM:
            return False
        
        self.current_style = style
        self.output_format.style = style
        
        # 更新配置
        if style in self.BUILTIN_STYLES:
            style_config = self.BUILTIN_STYLES[style]
            self.output_format.keep_coding_instructions = style_config.get('keep_coding_instructions', True)
        
        self._save_config()
        return True
    
    def set_custom_style(self, style_name: str) -> bool:
        """
        设置自定义样式
        
        Args:
            style_name: 自定义样式名称
        
        Returns:
            是否设置成功
        """
        if style_name not in self.custom_styles:
            return False
        
        self.current_style = OutputStyle.CUSTOM
        self.output_format.style = OutputStyle.CUSTOM
        self.output_format.custom_instructions = self.custom_styles[style_name].get('instructions', '')
        
        self._save_config()
        return True
    
    def set_structured_output(self, schema: Dict[str, Any]) -> None:
        """
        设置结构化输出
        
        Args:
            schema: JSON Schema 定义
        """
        self.output_format.structured = True
        self.output_format.schema = schema
    
    def clear_structured_output(self) -> None:
        """清除结构化输出"""
        self.output_format.structured = False
        self.output_format.schema = None
    
    def format_output(self, data: Any, style_override: OutputStyle = None) -> Any:
        """
        格式化输出
        
        Args:
            data: 输出数据
            style_override: 样式覆盖（可选）
        
        Returns:
            格式化后的输出
        """
        style = style_override or self.current_style
        
        # 结构化输出
        if self.output_format.structured and self.output_format.schema:
            return self._format_structured(data)
        
        # 样式化输出
        if style == OutputStyle.DEFAULT:
            return self._format_default(data)
        elif style == OutputStyle.EXPLANATORY:
            return self._format_explanatory(data)
        elif style == OutputStyle.LEARNING:
            return self._format_learning(data)
        elif style == OutputStyle.CUSTOM:
            return self._format_custom(data)
        
        return data
    
    def _format_structured(self, data: Any) -> Dict[str, Any]:
        """格式化结构化输出"""
        # 验证 schema
        if not self._validate_schema(data, self.output_format.schema):
            return {
                'error': 'Schema validation failed',
                'data': data
            }
        
        result = {'ok': True, 'value': data}
        
        if self.output_format.include_metadata:
            result['metadata'] = {
                'style': self.current_style.value,
                'schema': self.output_format.schema
            }
        
        return result
    
    def _format_default(self, data: Any) -> Any:
        """默认格式化"""
        if isinstance(data, dict):
            # Codong 风格
            if 'ok' in data:
                return data
            
            # 添加简洁建议
            if self.output_format.include_suggestions and 'suggestion' not in data:
                if 'error' in data:
                    data['suggestion'] = self._generate_suggestion(data['error'])
        
        return data
    
    def _format_explanatory(self, data: Any) -> Dict[str, Any]:
        """教育格式化"""
        result = {'output': data}
        
        if self.output_format.include_suggestions:
            result['insight'] = self._generate_insight(data)
        
        return result
    
    def _format_learning(self, data: Any) -> Dict[str, Any]:
        """学习格式化"""
        result = {'output': data}
        
        if self.output_format.include_suggestions:
            result['todo_human'] = self._generate_human_todo(data)
        
        return result
    
    def _format_custom(self, data: Any) -> Any:
        """自定义格式化"""
        # 应用自定义指令（简化实现）
        return data
    
    def create_custom_style(self, name: str, instructions: str, 
                           description: str = "", keep_coding: bool = False) -> bool:
        """
        创建自定义样式
        
        Args:
            name: 样式名称
            instructions: 自定义指令
            description: 描述
            keep_coding: 是否保留编码指令
        
        Returns:
            是否创建成功
        """
        self.custom_styles[name] = {
            'name': name,
            'description': description,
            'instructions': instructions,
            'keep_coding_instructions': keep_coding
        }
        
        self._save_config()
        return True
    
    def list_styles(self) -> List[Dict[str, str]]:
        """列出所有可用样式"""
        styles = []
        
        # 内置样式
        for style, config in self.BUILTIN_STYLES.items():
            styles.append({
                'name': config['name'],
                'type': 'builtin',
                'description': config['description']
            })
        
        # 自定义样式
        for name, config in self.custom_styles.items():
            styles.append({
                'name': name,
                'type': 'custom',
                'description': config.get('description', '')
            })
        
        return styles
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """验证数据是否符合 Schema（简化实现）"""
        if not schema:
            return True
        
        # 简化验证：只检查必需字段
        required = schema.get('required', [])
        if isinstance(data, dict):
            for field in required:
                if field not in data:
                    return False
        
        return True
    
    def _generate_suggestion(self, error: str) -> str:
        """生成修复建议"""
        suggestions = {
            'ESEC001': '使用安全的替代方案，如移动到 trash 而非 rm -rf',
            'ESEC002': '拆分为独立命令执行',
            'ECONFIG01': '检查配置项是否完整',
            'ETIMEOUT': '检查网络连接，或稍后重试',
        }
        
        for code, suggestion in suggestions.items():
            if code in str(error):
                return suggestion
        
        return '请检查错误信息并尝试修复'
    
    def _generate_insight(self, data: Any) -> str:
        """生成 Insight"""
        return f"[Insight] This operation uses best practice patterns"
    
    def _generate_human_todo(self, data: Any) -> str:
        """生成 TODO(human)"""
        return "# TODO(human): 实现自定义逻辑"
    
    def _load_config(self):
        """加载配置"""
        if not os.path.exists(self.config_path):
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 恢复样式
            style_str = config.get('outputStyle', 'default')
            self.current_style = OutputStyle(style_str.lower())
            
            # 恢复自定义样式
            self.custom_styles = config.get('customStyles', {})
            
        except Exception:
            pass
    
    def _save_config(self):
        """保存配置"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        config = {
            'outputStyle': self.current_style.value,
            'customStyles': self.custom_styles
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    
    def get_current_style_info(self) -> Dict[str, Any]:
        """获取当前样式信息"""
        if self.current_style == OutputStyle.CUSTOM:
            return {
                'style': 'custom',
                'config': self.output_format.custom_instructions[:100] + '...'
            }
        
        config = self.BUILTIN_STYLES.get(self.current_style, {})
        return {
            'style': self.current_style.value,
            'name': config.get('name', ''),
            'description': config.get('description', ''),
            'structured': self.output_format.structured
        }