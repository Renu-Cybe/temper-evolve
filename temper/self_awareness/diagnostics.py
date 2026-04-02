"""
诊断系统

提供系统健康检查和诊断功能
"""

from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"       # 未知


@dataclass
class HealthCheck:
    """健康检查项
    
    Attributes:
        name: 检查名称
        status: 健康状态
        message: 状态信息
        timestamp: 检查时间
        details: 详细信息
        duration_ms: 检查耗时（毫秒）
    """
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'duration_ms': self.duration_ms
        }


class Diagnostics:
    """诊断系统
    
    管理系统健康检查，支持：
    - 自定义健康检查
    - 定期检查
    - 健康状态聚合
    
    使用示例：
        diagnostics = Diagnostics()
        
        # 注册健康检查
        diagnostics.register_check("database", check_database)
        diagnostics.register_check("api", check_api)
        
        # 运行检查
        results = diagnostics.run_all_checks()
        
        # 获取整体状态
        status = diagnostics.get_overall_status()
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._last_results: Dict[str, HealthCheck] = {}
        self._lock = threading.RLock()
        self._running = False
        self._check_thread: Optional[threading.Thread] = None
        self._interval = 30  # 秒
        self._status_handlers: List[Callable[[HealthStatus, Dict], None]] = []
        self._last_status = HealthStatus.UNKNOWN
    
    def register_check(self, name: str, 
                       check_func: Callable[[], HealthCheck]) -> None:
        """注册健康检查
        
        Args:
            name: 检查名称
            check_func: 检查函数，返回 HealthCheck
        """
        with self._lock:
            self._checks[name] = check_func
    
    def unregister_check(self, name: str) -> bool:
        """注销健康检查"""
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                self._last_results.pop(name, None)
                return True
            return False
    
    def run_check(self, name: str) -> HealthCheck:
        """运行单个健康检查
        
        Args:
            name: 检查名称
            
        Returns:
            检查结果
        """
        with self._lock:
            check_func = self._checks.get(name)
        
        if not check_func:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not registered",
                timestamp=datetime.now()
            )
        
        start_time = time.time()
        try:
            result = check_func()
            result.duration_ms = (time.time() - start_time) * 1000
        except Exception as e:
            result = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000
            )
        
        with self._lock:
            self._last_results[name] = result
        
        # 检查状态变化
        self._check_status_change()
        
        return result
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """运行所有健康检查
        
        Returns:
            检查结果字典
        """
        with self._lock:
            check_names = list(self._checks.keys())
        
        results = {}
        for name in check_names:
            results[name] = self.run_check(name)
        
        return results
    
    def get_check_result(self, name: str) -> Optional[HealthCheck]:
        """获取指定检查的最新结果"""
        return self._last_results.get(name)
    
    def get_all_results(self) -> Dict[str, HealthCheck]:
        """获取所有检查的最新结果"""
        return self._last_results.copy()
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态
        
        规则：
        - 有任何 UNHEALTHY -> UNHEALTHY
        - 有 DEGRADED 但没有 UNHEALTHY -> DEGRADED
        - 全部 HEALTHY -> HEALTHY
        - 其他 -> UNKNOWN
        """
        with self._lock:
            results = list(self._last_results.values())
        
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in results]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_health_report(self) -> dict:
        """获取健康报告"""
        results = self.get_all_results()
        
        return {
            'overall_status': self.get_overall_status().value,
            'timestamp': datetime.now().isoformat(),
            'checks': {name: check.to_dict() for name, check in results.items()},
            'summary': {
                'total': len(results),
                'healthy': sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                'degraded': sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED),
                'unhealthy': sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY),
                'unknown': sum(1 for r in results.values() if r.status == HealthStatus.UNKNOWN)
            }
        }
    
    def register_status_handler(self, 
                                handler: Callable[[HealthStatus, Dict], None]) -> None:
        """注册状态变化处理器"""
        self._status_handlers.append(handler)
    
    def _check_status_change(self) -> None:
        """检查状态变化"""
        current_status = self.get_overall_status()
        
        if current_status != self._last_status:
            self._last_status = current_status
            
            report = self.get_health_report()
            for handler in self._status_handlers:
                try:
                    handler(current_status, report)
                except Exception as e:
                    print(f"Status handler error: {e}")
    
    def start_auto_check(self, interval: int = 30) -> None:
        """启动自动检查
        
        Args:
            interval: 检查间隔（秒）
        """
        if self._running:
            return
        
        self._interval = interval
        self._running = True
        self._check_thread = threading.Thread(
            target=self._check_loop,
            name="Diagnostics",
            daemon=True
        )
        self._check_thread.start()
    
    def stop_auto_check(self) -> None:
        """停止自动检查"""
        self._running = False
        if self._check_thread:
            self._check_thread.join(timeout=5)
    
    def _check_loop(self) -> None:
        """检查循环"""
        while self._running:
            self.run_all_checks()
            time.sleep(self._interval)


# 内置健康检查

def create_resource_health_check(metrics_collector, thresholds: dict) -> Callable[[], HealthCheck]:
    """创建资源健康检查
    
    Args:
        metrics_collector: 指标收集器
        thresholds: 阈值字典，如 {'cpu_percent': 80, 'memory_percent': 85}
        
    Returns:
        健康检查函数
    """
    def check() -> HealthCheck:
        issues = []
        
        for metric_name, threshold in thresholds.items():
            metric = metrics_collector.get_latest(metric_name)
            if metric and metric.value >= threshold:
                issues.append(f"{metric_name}: {metric.value:.1f}% (threshold: {threshold}%)")
        
        if issues:
            return HealthCheck(
                name="resource",
                status=HealthStatus.DEGRADED if len(issues) < len(thresholds) else HealthStatus.UNHEALTHY,
                message="; ".join(issues),
                timestamp=datetime.now(),
                details={'issues': issues}
            )
        
        return HealthCheck(
            name="resource",
            status=HealthStatus.HEALTHY,
            message="All resources within normal limits",
            timestamp=datetime.now()
        )
    
    return check
