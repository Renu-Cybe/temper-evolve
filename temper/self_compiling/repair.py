"""
代码修复器

检测和修复代码问题
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import ast
import re


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"    # 严重问题，必须修复
    HIGH = "high"            # 高优先级
    MEDIUM = "medium"        # 中优先级
    LOW = "low"              # 低优先级
    INFO = "info"            # 信息性


@dataclass
class CodeIssue:
    """代码问题
    
    Attributes:
        file_path: 文件路径
        line_number: 行号
        column: 列号
        severity: 严重程度
        message: 问题描述
        issue_type: 问题类型
        suggested_fix: 建议修复
        code_snippet: 相关代码片段
    """
    file_path: str
    line_number: int
    column: int
    severity: IssueSeverity
    message: str
    issue_type: str
    suggested_fix: Optional[str] = None
    code_snippet: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'column': self.column,
            'severity': self.severity.value,
            'message': self.message,
            'issue_type': self.issue_type,
            'suggested_fix': self.suggested_fix,
            'code_snippet': self.code_snippet
        }


@dataclass
class RepairProposal:
    """修复提案
    
    Attributes:
        issue: 要修复的问题
        original_code: 原始代码
        repaired_code: 修复后的代码
        confidence: 置信度 (0-1)
        description: 修复描述
        requires_confirmation: 是否需要用户确认
    """
    issue: CodeIssue
    original_code: str
    repaired_code: str
    confidence: float
    description: str
    requires_confirmation: bool = True
    
    def to_dict(self) -> dict:
        return {
            'issue': self.issue.to_dict(),
            'original_code': self.original_code,
            'repaired_code': self.repaired_code,
            'confidence': self.confidence,
            'description': self.description,
            'requires_confirmation': self.requires_confirmation
        }


class CodeRepair:
    """代码修复器
    
    检测和修复代码问题
    
    使用示例：
        repair = CodeRepair(audit_logger)
        
        # 注册检测器
        repair.register_detector(syntax_check_detector)
        
        # 注册修复策略
        repair.register_repair_strategy("syntax_error", syntax_fix_strategy)
        
        # 分析代码
        issues = repair.analyze("test.py", code)
        
        # 提出修复
        for issue in issues:
            proposal = repair.propose_repair(issue, code)
            if proposal:
                # 应用修复（需要确认）
                repair.apply_repair(proposal, confirmed=True)
    """
    
    def __init__(self, audit_logger=None):
        self._audit = audit_logger
        self._detectors: List[Callable[[str, str], List[CodeIssue]]] = []
        self._repair_strategies: Dict[str, Callable[[CodeIssue, str], Optional[RepairProposal]]] = {}
        
        # 注册内置检测器
        self._register_builtin_detectors()
    
    def _register_builtin_detectors(self) -> None:
        """注册内置检测器"""
        self._detectors.append(self._syntax_check)
        self._detectors.append(self._unused_import_check)
        self._detectors.append(self._bare_except_check)
    
    def register_detector(self, detector: Callable[[str, str], List[CodeIssue]]) -> None:
        """注册问题检测器"""
        self._detectors.append(detector)
    
    def register_repair_strategy(self, issue_type: str,
                                  strategy: Callable[[CodeIssue, str], Optional[RepairProposal]]) -> None:
        """注册修复策略"""
        self._repair_strategies[issue_type] = strategy
    
    def analyze(self, file_path: str, code: str) -> List[CodeIssue]:
        """分析代码问题
        
        Args:
            file_path: 文件路径
            code: 代码内容
            
        Returns:
            问题列表（按严重程度排序）
        """
        issues = []
        
        for detector in self._detectors:
            try:
                detected = detector(file_path, code)
                issues.extend(detected)
            except Exception as e:
                print(f"Detector error: {e}")
        
        # 按严重程度排序
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
            IssueSeverity.INFO: 4
        }
        issues.sort(key=lambda i: severity_order.get(i.severity, 5))
        
        return issues
    
    def propose_repair(self, issue: CodeIssue, code: str) -> Optional[RepairProposal]:
        """提出修复方案
        
        Args:
            issue: 代码问题
            code: 原始代码
            
        Returns:
            修复提案，无法修复返回 None
        """
        strategy = self._repair_strategies.get(issue.issue_type)
        if strategy:
            return strategy(issue, code)
        
        # 使用默认修复策略
        return self._default_repair(issue, code)
    
    def apply_repair(self, proposal: RepairProposal, 
                     confirmed: bool = False) -> bool:
        """应用修复
        
        Args:
            proposal: 修复提案
            confirmed: 是否已确认
            
        Returns:
            是否应用成功
        """
        if proposal.requires_confirmation and not confirmed:
            # 记录待确认的修复
            if self._audit:
                self._audit.info(
                    category="self_compiling",
                    action="repair.pending",
                    source="CodeRepair",
                    parameters={
                        'file': proposal.issue.file_path,
                        'issue_type': proposal.issue.issue_type,
                        'confidence': proposal.confidence
                    }
                )
            return False
        
        # 实际应用修复（这里应该调用文件系统工具）
        # 简化实现：仅记录
        if self._audit:
            self._audit.info(
                category="self_compiling",
                action="repair.applied",
                source="CodeRepair",
                parameters={
                    'file': proposal.issue.file_path,
                    'issue_type': proposal.issue.issue_type,
                    'confidence': proposal.confidence
                }
            )
        
        return True
    
    # 内置检测器
    
    def _syntax_check(self, file_path: str, code: str) -> List[CodeIssue]:
        """语法检查"""
        issues = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line_number=e.lineno or 1,
                column=e.offset or 0,
                severity=IssueSeverity.CRITICAL,
                message=f"Syntax error: {e.msg}",
                issue_type="syntax_error",
                suggested_fix=None,
                code_snippet=e.text
            ))
        except Exception as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line_number=1,
                column=0,
                severity=IssueSeverity.CRITICAL,
                message=f"Parse error: {e}",
                issue_type="parse_error"
            ))
        
        return issues
    
    def _unused_import_check(self, file_path: str, code: str) -> List[CodeIssue]:
        """未使用导入检查"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            # 收集导入
            imports = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[alias.asname or alias.name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        imports[name] = node.lineno
            
            # 收集使用的名称
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # 找出未使用的导入
            for name, lineno in imports.items():
                if name not in used_names and name != '*':
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line_number=lineno,
                        column=0,
                        severity=IssueSeverity.LOW,
                        message=f"Unused import: {name}",
                        issue_type="unused_import",
                        suggested_fix=f"Remove import {name}"
                    ))
        
        except Exception:
            pass
        
        return issues
    
    def _bare_except_check(self, file_path: str, code: str) -> List[CodeIssue]:
        """裸 except 检查"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            column=0,
                            severity=IssueSeverity.MEDIUM,
                            message="Bare 'except' clause - should specify exception type",
                            issue_type="bare_except",
                            suggested_fix="Use 'except Exception:' instead of bare 'except:'"
                        ))
        
        except Exception:
            pass
        
        return issues
    
    def _default_repair(self, issue: CodeIssue, code: str) -> Optional[RepairProposal]:
        """默认修复策略"""
        # 简化实现：仅对未使用导入提供修复
        if issue.issue_type == "unused_import":
            lines = code.split('\n')
            if 1 <= issue.line_number <= len(lines):
                original = lines[issue.line_number - 1]
                # 返回删除该行的修复
                return RepairProposal(
                    issue=issue,
                    original_code=original,
                    repaired_code="# " + original,  # 注释掉而不是删除
                    confidence=0.8,
                    description=f"Comment out unused import: {issue.message}",
                    requires_confirmation=True
                )
        
        return None
