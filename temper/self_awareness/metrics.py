"""
指标收集器

负责收集和存储系统指标
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import threading
import time


class MetricType(Enum):
    """指标类型"""
    GAUGE = "gauge"           # 瞬时值
    COUNTER = "counter"       # 累计值
    HISTOGRAM = "histogram"   # 分布值


@dataclass
class MetricValue:
    """指标值
    
    Attributes:
        name: 指标名称
        value: 指标值
        metric_type: 指标类型
        timestamp: 采集时间
        labels: 标签（用于多维度）
        unit: 单位
    """
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'unit': self.unit
        }


class MetricsCollector:
    """指标收集器
    
    负责收集和存储系统指标，支持：
    - 自动采集
    - 历史查询
    - 阈值告警
    
    使用示例：
        collector = MetricsCollector()
        
        # 注册自定义收集器
        collector.register("custom_metric", lambda: MetricValue(...))
        
        # 启动自动采集
        collector.start_collection(interval=10)
        
        # 获取历史
        history = collector.get_history("cpu_percent", limit=100)
    """
    
    def __init__(self, max_history: int = 10000):
        self._collectors: Dict[str, Callable[[], MetricValue]] = {}
        self._metrics_history: List[MetricValue] = []
        self._lock = threading.RLock()
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._interval = 10  # 秒
        self._max_history = max_history
        self._alert_handlers: List[Callable[[MetricValue, float], None]] = []
        self._thresholds: Dict[str, float] = {}
    
    def register(self, name: str, 
                 collector: Callable[[], MetricValue]) -> None:
        """注册指标收集器
        
        Args:
            name: 指标名称
            collector: 收集器函数，返回 MetricValue
        """
        with self._lock:
            self._collectors[name] = collector
    
    def unregister(self, name: str) -> bool:
        """注销指标收集器"""
        with self._lock:
            if name in self._collectors:
                del self._collectors[name]
                return True
            return False
    
    def collect(self) -> List[MetricValue]:
        """执行一次指标收集
        
        Returns:
            收集到的指标列表
        """
        metrics = []
        with self._lock:
            collectors = list(self._collectors.items())
        
        for name, collector in collectors:
            try:
                metric = collector()
                metrics.append(metric)
                
                # 检查阈值告警
                self._check_alert(metric)
            except Exception as e:
                print(f"Failed to collect metric {name}: {e}")
        
        with self._lock:
            self._metrics_history.extend(metrics)
            # 限制历史大小
            if len(self._metrics_history) > self._max_history:
                self._metrics_history = self._metrics_history[-(self._max_history // 2):]
        
        return metrics
    
    def get_history(self, name: Optional[str] = None, 
                    limit: int = 100,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[MetricValue]:
        """获取指标历史
        
        Args:
            name: 指标名称，None 表示所有
            limit: 返回数量限制
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            指标历史列表
        """
        with self._lock:
            history = self._metrics_history.copy()
        
        if name:
            history = [m for m in history if m.name == name]
        
        if start_time:
            history = [m for m in history if m.timestamp >= start_time]
        
        if end_time:
            history = [m for m in history if m.timestamp <= end_time]
        
        return history[-limit:]
    
    def get_latest(self, name: str) -> Optional[MetricValue]:
        """获取最新指标值"""
        history = self.get_history(name, limit=1)
        return history[0] if history else None
    
    def get_average(self, name: str, 
                    window_seconds: int = 300) -> Optional[float]:
        """获取指标平均值
        
        Args:
            name: 指标名称
            window_seconds: 时间窗口（秒）
            
        Returns:
            平均值，无数据返回 None
        """
        from datetime import timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=window_seconds)
        
        history = self.get_history(name, start_time=start_time, end_time=end_time)
        
        if not history:
            return None
        
        return sum(m.value for m in history) / len(history)
    
    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """设置指标阈值"""
        self._thresholds[metric_name] = threshold
    
    def register_alert_handler(self, 
                               handler: Callable[[MetricValue, float], None]) -> None:
        """注册告警处理器"""
        self._alert_handlers.append(handler)
    
    def _check_alert(self, metric: MetricValue) -> None:
        """检查是否需要触发告警"""
        threshold = self._thresholds.get(metric.name)
        if threshold is None:
            return
        
        if metric.value >= threshold:
            for handler in self._alert_handlers:
                try:
                    handler(metric, threshold)
                except Exception as e:
                    print(f"Alert handler error: {e}")
    
    def start_collection(self, interval: int = 10) -> None:
        """启动自动收集
        
        Args:
            interval: 收集间隔（秒）
        """
        if self._running:
            return
        
        self._interval = interval
        self._running = True
        self._collection_thread = threading.Thread(
            target=self._collection_loop, 
            name="MetricsCollector",
            daemon=True
        )
        self._collection_thread.start()
    
    def stop_collection(self) -> None:
        """停止自动收集"""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)
    
    def _collection_loop(self) -> None:
        """收集循环"""
        while self._running:
            self.collect()
            time.sleep(self._interval)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            return {
                'collectors_count': len(self._collectors),
                'history_size': len(self._metrics_history),
                'running': self._running,
                'interval': self._interval
            }
    
    def export_metrics(self, format: str = 'json') -> str:
        """导出指标
        
        Args:
            format: 导出格式 ('json', 'prometheus')
            
        Returns:
            导出的指标字符串
        """
        if format == 'json':
            import json
            history = self.get_history(limit=1000)
            return json.dumps([m.to_dict() for m in history], indent=2)
        
        elif format == 'prometheus':
            lines = []
            history = self.get_history(limit=1000)
            
            # 按名称分组
            by_name: Dict[str, List[MetricValue]] = {}
            for m in history:
                if m.name not in by_name:
                    by_name[m.name] = []
                by_name[m.name].append(m)
            
            for name, metrics in by_name.items():
                # 只导出最新值
                latest = max(metrics, key=lambda m: m.timestamp)
                labels = ','.join(f'{k}="{v}"' for k, v in latest.labels.items())
                if labels:
                    lines.append(f'{name}{{{labels}}} {latest.value}')
                else:
                    lines.append(f'{name} {latest.value}')
            
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unknown format: {format}")
