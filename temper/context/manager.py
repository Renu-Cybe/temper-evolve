#!/usr/bin/env python3
"""
Context Manager - 三层上下文管理系统

基于 Claude Code 的上下文工程最佳实践：
- L1: 系统层（核心指令 + 工具定义）
- L2: 项目层（CLAUDE.md + Skills）
- L3: 会话层（对话历史 + 运行状态）

关键技术：
- Token 预算管理
- 按需加载
- 上下文压缩
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import os


@dataclass
class TokenBudget:
    """Token 预算配置"""
    max_total: int = 200000  # 最大总 Token
    reserved_for_compaction: float = 0.22  # 22% 预留给压缩
    system_layer_max: float = 0.20  # 20% 系统层
    project_layer_max: float = 0.30  # 30% 项目层
    session_layer_max: float = 0.28  # 28% 会话层
    
    @property
    def usable_tokens(self) -> int:
        """可用 Token（扣除预留）"""
        return int(self.max_total * (1 - self.reserved_for_compaction))
    
    @property
    def system_max(self) -> int:
        return int(self.usable_tokens * self.system_layer_max)
    
    @property
    def project_max(self) -> int:
        return int(self.usable_tokens * self.project_layer_max)
    
    @property
    def session_max(self) -> int:
        return int(self.usable_tokens * self.session_layer_max)


@dataclass
class ContextLayer:
    """上下文层"""
    name: str
    content: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    max_tokens: int = 0
    loaded: bool = False
    last_updated: Optional[datetime] = None
    
    def add_content(self, key: str, value: Any, tokens: int) -> bool:
        """添加内容到上下文层"""
        if self.token_count + tokens > self.max_tokens:
            return False  # 超出预算
        
        self.content[key] = value
        self.token_count += tokens
        self.last_updated = datetime.now()
        return True
    
    def remove_content(self, key: str) -> bool:
        """移除内容"""
        if key in self.content:
            del self.content[key]
            self.last_updated = datetime.now()
            return True
        return False
    
    def clear(self):
        """清空层"""
        self.content.clear()
        self.token_count = 0
        self.last_updated = datetime.now()


class ContextManager:
    """
    三层上下文管理器
    
    使用示例:
        manager = ContextManager()
        
        # 添加系统层内容
        manager.add_system_content("core_instructions", "你是 Temper Agent...", 500)
        
        # 按需加载项目层
        manager.load_project_skill("heartbeat_evolver")
        
        # 添加会话层内容
        manager.add_session_content("user_query", "检查系统健康", 50)
        
        # 构建完整上下文
        context = manager.build_context()
        
        # 压缩上下文
        manager.compact_session_layer()
    """
    
    def __init__(self, budget: Optional[TokenBudget] = None):
        self.budget = budget or TokenBudget()
        
        # 三层上下文
        self.system_layer = ContextLayer(
            name="system",
            max_tokens=self.budget.system_max
        )
        self.project_layer = ContextLayer(
            name="project",
            max_tokens=self.budget.project_max
        )
        self.session_layer = ContextLayer(
            name="session",
            max_tokens=self.budget.session_max
        )
        
        # 已加载的 Skills（按需加载）
        self.loaded_skills: Dict[str, dict] = {}
        
        # 压缩统计
        self.compaction_stats = {
            'total_compactions': 0,
            'tokens_saved': 0,
            'last_compaction': None
        }
    
    def add_system_content(self, key: str, content: str, estimated_tokens: int = None) -> bool:
        """
        添加系统层内容
        
        Args:
            key: 内容标识
            content: 内容文本
            estimated_tokens: 估计 Token 数（可选，自动计算）
        
        Returns:
            是否添加成功
        """
        if estimated_tokens is None:
            estimated_tokens = len(content) // 4  # 粗略估计
        
        return self.system_layer.add_content(key, content, estimated_tokens)
    
    def load_project_skill(self, skill_name: str, skill_path: str = None) -> bool:
        """
        按需加载项目层 Skill
        
        Args:
            skill_name: Skill 名称
            skill_path: Skill 路径（可选）
        
        Returns:
            是否加载成功
        """
        # 已加载则跳过
        if skill_name in self.loaded_skills:
            return True
        
        # 尝试加载 Skill 文件
        if skill_path is None:
            skill_path = f"temper/skills/{skill_name}/SKILL.md"
        
        if not os.path.exists(skill_path):
            return False
        
        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tokens = len(content) // 4
            
            if self.project_layer.add_content(f"skill:{skill_name}", content, tokens):
                self.loaded_skills[skill_name] = {
                    'path': skill_path,
                    'tokens': tokens,
                    'loaded_at': datetime.now().isoformat()
                }
                return True
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Failed to load skill {skill_name}: {e}")
            return False
    
    def unload_project_skill(self, skill_name: str) -> bool:
        """卸载 Skill"""
        if skill_name not in self.loaded_skills:
            return False
        
        if self.project_layer.remove_content(f"skill:{skill_name}"):
            del self.loaded_skills[skill_name]
            return True
        
        return False
    
    def add_session_content(self, key: str, content: Any, tokens: int) -> bool:
        """添加会话层内容"""
        return self.session_layer.add_content(key, content, tokens)
    
    def build_context(self, include_skills: List[str] = None) -> Dict[str, Any]:
        """
        构建完整上下文
        
        Args:
            include_skills: 要包含的 Skills（可选，默认全部）
        
        Returns:
            完整上下文字典
        """
        context = {
            'system': self.system_layer.content,
            'project': {},
            'session': self.session_layer.content,
            'metadata': {
                'token_usage': {
                    'system': self.system_layer.token_count,
                    'project': self.project_layer.token_count,
                    'session': self.session_layer.token_count,
                    'total': self.total_tokens,
                    'budget': self.budget.usable_tokens
                },
                'loaded_skills': list(self.loaded_skills.keys()),
                'last_updated': datetime.now().isoformat()
            }
        }
        
        # 按需包含 Skills
        if include_skills:
            for skill in include_skills:
                key = f"skill:{skill}"
                if key in self.project_layer.content:
                    context['project'][key] = self.project_layer.content[key]
        else:
            context['project'] = self.project_layer.content
        
        return context
    
    def compact_session_layer(self, keep_last_n: int = 10) -> Dict[str, Any]:
        """
        压缩会话层
        
        Args:
            keep_last_n: 保留最近 N 条记录
        
        Returns:
            压缩后的摘要
        """
        if len(self.session_layer.content) <= keep_last_n:
            return {'compacted': False, 'reason': 'below_threshold'}
        
        # 获取所有内容
        items = list(self.session_layer.content.items())
        
        # 保留最近 N 条
        recent_items = items[-keep_last_n:]
        old_items = items[:-keep_last_n]
        
        # 生成压缩摘要
        summary = {
            'compacted': True,
            'items_removed': len(old_items),
            'tokens_saved': sum(
                len(str(v)) // 4 for k, v in old_items
            ),
            'summary': self._generate_summary(old_items),
            'compacted_at': datetime.now().isoformat()
        }
        
        # 更新统计
        self.compaction_stats['total_compactions'] += 1
        self.compaction_stats['tokens_saved'] += summary['tokens_saved']
        self.compaction_stats['last_compaction'] = datetime.now().isoformat()
        
        # 重建会话层
        self.session_layer.clear()
        for key, value in recent_items:
            tokens = len(str(value)) // 4
            self.session_layer.add_content(key, value, tokens)
        
        # 添加压缩摘要
        summary_tokens = len(str(summary)) // 4
        self.session_layer.add_content('_compaction_summary', summary, summary_tokens)
        
        return summary
    
    def _generate_summary(self, items: List[tuple]) -> str:
        """生成压缩摘要"""
        summary_parts = []
        for key, value in items[:5]:  # 只摘要前5个
            value_str = str(value)[:100]  # 截断
            summary_parts.append(f"- {key}: {value_str}...")
        
        if len(items) > 5:
            summary_parts.append(f"... and {len(items) - 5} more items")
        
        return "\n".join(summary_parts)
    
    @property
    def total_tokens(self) -> int:
        """总 Token 数"""
        return (
            self.system_layer.token_count +
            self.project_layer.token_count +
            self.session_layer.token_count
        )
    
    @property
    def utilization_rate(self) -> float:
        """上下文利用率"""
        return self.total_tokens / self.budget.usable_tokens
    
    def get_status(self) -> Dict[str, Any]:
        """获取上下文状态"""
        return {
            'token_usage': {
                'system': {
                    'count': self.system_layer.token_count,
                    'max': self.system_layer.max_tokens,
                    'percent': self.system_layer.token_count / self.system_layer.max_tokens * 100
                },
                'project': {
                    'count': self.project_layer.token_count,
                    'max': self.project_layer.max_tokens,
                    'percent': self.project_layer.token_count / self.project_layer.max_tokens * 100
                },
                'session': {
                    'count': self.session_layer.token_count,
                    'max': self.session_layer.max_tokens,
                    'percent': self.session_layer.token_count / self.session_layer.max_tokens * 100
                },
                'total': {
                    'count': self.total_tokens,
                    'max': self.budget.usable_tokens,
                    'percent': self.utilization_rate * 100
                }
            },
            'loaded_skills': self.loaded_skills,
            'compaction_stats': self.compaction_stats
        }