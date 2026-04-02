"""
策略引擎

定义和执行自适应策略
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading


class StrategyType(Enum):
    """策略类型"""
    THRESHOLD = "threshold"       # 阈值策略
    PREDICTIVE = "predictive"     # 预测策略
    REINFORCEMENT = "rl"          # 强化学习策略
    RULE_BASED = "rule_based"     # 规则策略


@dataclass
class AdaptiveStrategy:
    """自适应策略
    
    Attributes:
        name: 策略名称
        strategy_type: 策略类型
        conditions: 触发条件列表
        actions: 执行动作列表
        priority: 优先级（数字越大优先级越高）
        enabled: 是否启用
        cooldown_seconds: 冷却时间（秒）
        last_triggered: 上次触发时间
    """
    name: str
    strategy_type: StrategyType
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True
    cooldown_seconds: int = 60
    last_triggered: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'type': self.strategy_type.value,
            'conditions': self.conditions,
            'actions': self.actions,
            'priority': self.priority,
            'enabled': self.enabled,
            'cooldown_seconds': self.cooldown_seconds
        }


@dataclass
class StrategyExecution:
    """策略执行记录"""
    strategy_name: str
    triggered_at: datetime
    conditions_matched: List[str]
    actions_executed: List[str]
    success: bool
    error_message: Optional[str] = None


class StrategyEngine:
    """策略引擎
    
    管理和执行自适应策略
    
    使用示例：
        engine = StrategyEngine(metrics_collector, parameter_tuner)
        
        # 注册策略
        engine.register_strategy(AdaptiveStrategy(
            name="high_cpu_response",
            strategy_type=StrategyType.THRESHOLD,
            conditions=[{
                'metric': 'cpu_percent',
                'operator': '>',
                'value': 80
            }],
            actions=[{
                'type': 'tune_parameter',
                'parameter': 'max_workers',
                'adjustment': -1
            }]
        ))
        
        # 评估策略
        triggered = engine.evaluate()
    """
    
    def __init__(self, metrics_collector, parameter_tuner):
        self._metrics = metrics_collector
        self._tuner = parameter_tuner
        self._strategies: List[AdaptiveStrategy] = []
        self._action_handlers: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._execution_history: List[StrategyExecution] = []
        
        # 注册内置动作处理器
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self) -> None:
        """注册内置动作处理器"""
        self._action_handlers['tune_parameter'] = self._handle_tune_parameter
        self._action_handlers['set_threshold'] = self._handle_set_threshold
        self._action_handlers['log_message'] = self._handle_log_message
    
    def register_strategy(self, strategy: AdaptiveStrategy) -> None:
        """注册策略"""
        with self._lock:
            self._strategies.append(strategy)
            # 按优先级排序
            self._strategies.sort(key=lambda s: s.priority, reverse=True)
    
    def unregister_strategy(self, name: str) -> bool:
        """注销策略"""
        with self._lock:
            for i, strategy in enumerate(self._strategies):
                if strategy.name == name:
                    del self._strategies[i]
                    return True
            return False
    
    def enable_strategy(self, name: str) -> bool:
        """启用策略"""
        with self._lock:
            for strategy in self._strategies:
                if strategy.name == name:
                    strategy.enabled = True
                    return True
            return False
    
    def disable_strategy(self, name: str) -> bool:
        """禁用策略"""
        with self._lock:
            for strategy in self._strategies:
                if strategy.name == name:
                    strategy.enabled = False
                    return True
            return False
    
    def register_action_handler(self, action_type: str, 
                                handler: Callable[[Dict], Any]) -> None:
        """注册动作处理器"""
        self._action_handlers[action_type] = handler
    
    def evaluate(self) -> List[StrategyExecution]:
        """评估所有策略
        
        Returns:
            触发的策略执行记录列表
        """
        triggered = []
        
        with self._lock:
            strategies = self._strategies.copy()
        
        for strategy in strategies:
            if not strategy.enabled:
                continue
            
            # 检查冷却时间
            if strategy.last_triggered:
                elapsed = (datetime.now() - strategy.last_triggered).total_seconds()
                if elapsed < strategy.cooldown_seconds:
                    continue
            
            # 检查条件
            matched_conditions = self._check_conditions(strategy.conditions)
            
            if matched_conditions:
                # 执行动作
                execution = self._execute_strategy(strategy, matched_conditions)
                triggered.append(execution)
                
                # 更新上次触发时间
                strategy.last_triggered = datetime.now()
        
        # 记录执行历史
        with self._lock:
            self._execution_history.extend(triggered)
        
        return triggered
    
    def _check_conditions(self, conditions: List[Dict]) -> List[str]:
        """检查条件是否满足
        
        Args:
            conditions: 条件列表
            
        Returns:
            满足的条件名称列表
        """
        matched = []
        
        for condition in conditions:
            if self._evaluate_condition(condition):
                matched.append(condition.get('name', 'unnamed'))
        
        return matched
    
    def _evaluate_condition(self, condition: Dict) -> bool:
        """评估单个条件"""
        condition_type = condition.get('type', 'metric')
        
        if condition_type == 'metric':
            return self._evaluate_metric_condition(condition)
        elif condition_type == 'time':
            return self._evaluate_time_condition(condition)
        elif condition_type == 'custom':
            handler = condition.get('handler')
            if handler:
                return handler()
        
        return False
    
    def _evaluate_metric_condition(self, condition: Dict) -> bool:
        """评估指标条件"""
        metric_name = condition.get('metric')
        operator = condition.get('operator', '>')
        threshold = condition.get('value')
        
        if not metric_name or threshold is None:
            return False
        
        metric = self._metrics.get_latest(metric_name)
        if not metric:
            return False
        
        value = metric.value
        
        if operator == '>':
            return value > threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<':
            return value < threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        
        return False
    
    def _evaluate_time_condition(self, condition: Dict) -> bool:
        """评估时间条件"""
        # 简化实现
        return True
    
    def _execute_strategy(self, strategy: AdaptiveStrategy,
                          matched_conditions: List[str]) -> StrategyExecution:
        """执行策略"""
        executed_actions = []
        success = True
        error_message = None
        
        for action in strategy.actions:
            action_type = action.get('type')
            handler = self._action_handlers.get(action_type)
            
            if handler:
                try:
                    handler(action)
                    executed_actions.append(action_type)
                except Exception as e:
                    success = False
                    error_message = str(e)
                    break
            else:
                executed_actions.append(f"{action_type}(no handler)")
        
        execution = StrategyExecution(
            strategy_name=strategy.name,
            triggered_at=datetime.now(),
            conditions_matched=matched_conditions,
            actions_executed=executed_actions,
            success=success,
            error_message=error_message
        )
        
        return execution
    
    # 内置动作处理器
    
    def _handle_tune_parameter(self, action: Dict) -> None:
        """处理参数调整动作"""
        param_name = action.get('parameter')
        adjustment = action.get('adjustment', 0)
        
        if param_name and adjustment:
            param = self._tuner.get_parameter(param_name)
            if param:
                new_value = param.current_value + adjustment
                self._tuner.set_value(param_name, new_value)
    
    def _handle_set_threshold(self, action: Dict) -> None:
        """处理阈值设置动作"""
        metric_name = action.get('metric')
        threshold = action.get('threshold')
        
        if metric_name and threshold is not None:
            self._metrics.set_threshold(metric_name, threshold)
    
    def _handle_log_message(self, action: Dict) -> None:
        """处理日志动作"""
        message = action.get('message', '')
        level = action.get('level', 'info')
        print(f"[{level.upper()}] {message}")
    
    def get_execution_history(self, 
                              strategy_name: str = None,
                              limit: int = 100) -> List[StrategyExecution]:
        """获取执行历史"""
        with self._lock:
            history = self._execution_history.copy()
        
        if strategy_name:
            history = [h for h in history if h.strategy_name == strategy_name]
        
        return history[-limit:]
    
    def get_strategies(self, enabled_only: bool = False) -> List[AdaptiveStrategy]:
        """获取所有策略"""
        with self._lock:
            strategies = self._strategies.copy()
        
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]
        
        return strategies
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                'strategies_count': len(self._strategies),
                'enabled_count': sum(1 for s in self._strategies if s.enabled),
                'execution_history_size': len(self._execution_history)
            }
