"""
参数调优器

根据系统指标动态调整参数
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Optional, Union
from datetime import datetime
import threading
import time


@dataclass
class Parameter:
    """可调参数
    
    Attributes:
        name: 参数名称
        current_value: 当前值
        min_value: 最小值
        max_value: 最大值
        step: 调整步长
        description: 描述
    """
    name: str
    current_value: Any
    min_value: Any
    max_value: Any
    step: Any
    description: str = ""
    
    def is_valid(self, value: Any) -> bool:
        """检查值是否在有效范围内"""
        return self.min_value <= value <= self.max_value


@dataclass
class TuningResult:
    """调优结果
    
    Attributes:
        parameter: 参数名称
        old_value: 原值
        new_value: 新值
        reason: 调整原因
        timestamp: 调整时间
        metrics_before: 调整前指标
        metrics_after: 调整后指标
        improvement: 改进百分比
    """
    parameter: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: datetime
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'parameter': self.parameter,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'metrics_before': self.metrics_before,
            'metrics_after': self.metrics_after,
            'improvement': self.improvement
        }


class ParameterTuner:
    """参数调优器
    
    根据系统指标动态调整参数
    
    使用示例：
        tuner = ParameterTuner(metrics_collector)
        
        # 注册参数
        tuner.register_parameter(Parameter(
            name="max_workers",
            current_value=4,
            min_value=1,
            max_value=16,
            step=1
        ))
        
        # 执行调优
        result = tuner.tune("max_workers", "High CPU usage detected")
    """
    
    def __init__(self, metrics_collector):
        self._metrics = metrics_collector
        self._parameters: Dict[str, Parameter] = {}
        self._adjusters: Dict[str, Callable[[Parameter, Dict], Any]] = {}
        self._history: List[TuningResult] = []
        self._lock = threading.RLock()
        self._running = False
        self._auto_tune_thread: Optional[threading.Thread] = None
        self._interval = 300  # 秒
        self._tuning_handlers: List[Callable[[TuningResult], None]] = []
    
    def register_parameter(self, param: Parameter) -> None:
        """注册可调参数"""
        with self._lock:
            self._parameters[param.name] = param
    
    def unregister_parameter(self, name: str) -> bool:
        """注销参数"""
        with self._lock:
            if name in self._parameters:
                del self._parameters[name]
                self._adjusters.pop(name, None)
                return True
            return False
    
    def register_adjuster(self, param_name: str, 
                          adjuster: Callable[[Parameter, Dict], Any]) -> None:
        """注册参数调整器
        
        Args:
            param_name: 参数名称
            adjuster: 调整函数，接收参数和指标，返回新值
        """
        with self._lock:
            self._adjusters[param_name] = adjuster
    
    def get_parameter(self, name: str) -> Optional[Parameter]:
        """获取参数信息"""
        return self._parameters.get(name)
    
    def get_value(self, name: str) -> Any:
        """获取参数当前值"""
        param = self._parameters.get(name)
        return param.current_value if param else None
    
    def set_value(self, name: str, value: Any) -> bool:
        """手动设置参数值"""
        with self._lock:
            param = self._parameters.get(name)
            if not param:
                return False
            
            if not param.is_valid(value):
                return False
            
            param.current_value = value
            return True
    
    def tune(self, param_name: str, 
             reason: str = "") -> Optional[TuningResult]:
        """调优指定参数
        
        Args:
            param_name: 参数名称
            reason: 调整原因
            
        Returns:
            调优结果，参数不存在或无调整返回 None
        """
        with self._lock:
            param = self._parameters.get(param_name)
            if not param:
                return None
            
            # 获取当前指标
            metrics_before = self._get_current_metrics()
            
            # 执行调整
            adjuster = self._adjusters.get(param_name)
            if adjuster:
                new_value = adjuster(param, metrics_before)
            else:
                new_value = self._default_adjust(param, metrics_before)
            
            # 检查是否有变化
            if new_value == param.current_value:
                return None
            
            old_value = param.current_value
            param.current_value = new_value
        
        # 等待并获取新指标
        time.sleep(1)
        metrics_after = self._get_current_metrics()
        
        # 计算改进
        improvement = self._calculate_improvement(
            metrics_before, metrics_after
        )
        
        result = TuningResult(
            parameter=param_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            timestamp=datetime.now(),
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            improvement=improvement
        )
        
        with self._lock:
            self._history.append(result)
        
        # 通知处理器
        for handler in self._tuning_handlers:
            try:
                handler(result)
            except Exception as e:
                print(f"Tuning handler error: {e}")
        
        return result
    
    def _get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        metrics = {}
        
        # 获取常见指标
        for name in ['cpu_percent', 'memory_percent', 'disk_percent']:
            metric = self._metrics.get_latest(name)
            if metric:
                metrics[name] = metric.value
        
        return metrics
    
    def _default_adjust(self, param: Parameter, 
                        metrics: Dict[str, float]) -> Any:
        """默认调整逻辑
        
        根据资源使用情况简单调整
        """
        current = param.current_value
        
        if isinstance(current, (int, float)):
            cpu = metrics.get('cpu_percent', 50)
            memory = metrics.get('memory_percent', 50)
            
            # 高负载时减少
            if cpu > 80 or memory > 85:
                new_value = max(param.min_value, current - param.step)
            # 低负载时增加
            elif cpu < 30 and memory < 50:
                new_value = min(param.max_value, current + param.step)
            else:
                new_value = current
            
            # 整数类型处理
            if isinstance(current, int):
                new_value = int(new_value)
            
            return new_value
        
        return current
    
    def _calculate_improvement(self, 
                               before: Dict[str, float],
                               after: Dict[str, float]) -> float:
        """计算改进百分比"""
        if not before or not after:
            return 0.0
        
        improvements = []
        for key in before:
            if key in after:
                # 假设指标越低越好
                if before[key] > 0:
                    improvement = (before[key] - after[key]) / before[key] * 100
                    improvements.append(improvement)
        
        return sum(improvements) / len(improvements) if improvements else 0.0
    
    def auto_tune(self, param_names: List[str] = None) -> List[TuningResult]:
        """自动调优多个参数
        
        Args:
            param_names: 要调优的参数列表，None 表示全部
            
        Returns:
            调优结果列表
        """
        if param_names is None:
            param_names = list(self._parameters.keys())
        
        results = []
        for name in param_names:
            result = self.tune(name, "Auto-tuning")
            if result:
                results.append(result)
        
        return results
    
    def start_auto_tuning(self, interval: int = 300) -> None:
        """启动自动调优
        
        Args:
            interval: 调优间隔（秒）
        """
        if self._running:
            return
        
        self._interval = interval
        self._running = True
        self._auto_tune_thread = threading.Thread(
            target=self._auto_tune_loop,
            name="ParameterTuner",
            daemon=True
        )
        self._auto_tune_thread.start()
    
    def stop_auto_tuning(self) -> None:
        """停止自动调优"""
        self._running = False
        if self._auto_tune_thread:
            self._auto_tune_thread.join(timeout=5)
    
    def _auto_tune_loop(self) -> None:
        """自动调优循环"""
        while self._running:
            self.auto_tune()
            time.sleep(self._interval)
    
    def get_history(self, param_name: str = None, 
                    limit: int = 100) -> List[TuningResult]:
        """获取调优历史"""
        with self._lock:
            history = self._history.copy()
        
        if param_name:
            history = [h for h in history if h.parameter == param_name]
        
        return history[-limit:]
    
    def register_tuning_handler(self, 
                                handler: Callable[[TuningResult], None]) -> None:
        """注册调优处理器"""
        self._tuning_handlers.append(handler)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                'parameters_count': len(self._parameters),
                'history_size': len(self._history),
                'auto_tuning': self._running
            }
