"""
资源监控器

监控系统资源使用情况
"""

from typing import Optional
from .metrics import MetricsCollector, MetricValue, MetricType
from datetime import datetime


class ResourceMonitor:
    """资源监控器
    
    监控 CPU、内存、磁盘、网络等资源使用情况
    
    使用示例：
        collector = MetricsCollector()
        monitor = ResourceMonitor(collector)
        
        # 指标会自动收集到 collector 中
        cpu_metric = collector.get_latest("cpu_percent")
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics = metrics_collector
        self._register_default_collectors()
    
    def _register_default_collectors(self) -> None:
        """注册默认资源收集器"""
        
        # CPU 使用率
        self._metrics.register("cpu_percent", self._collect_cpu)
        
        # 内存使用
        self._metrics.register("memory_percent", self._collect_memory)
        self._metrics.register("memory_used_mb", self._collect_memory_used)
        self._metrics.register("memory_available_mb", self._collect_memory_available)
        
        # 磁盘使用
        self._metrics.register("disk_percent", self._collect_disk)
        self._metrics.register("disk_used_gb", self._collect_disk_used)
        self._metrics.register("disk_free_gb", self._collect_disk_free)
        
        # 网络 IO
        self._metrics.register("net_io_sent_mb", self._collect_net_sent)
        self._metrics.register("net_io_recv_mb", self._collect_net_recv)
        
        # 进程信息
        self._metrics.register("process_count", self._collect_process_count)
    
    def _collect_cpu(self) -> MetricValue:
        """收集 CPU 使用率"""
        try:
            import psutil
            value = psutil.cpu_percent(interval=None)
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="cpu_percent",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_memory(self) -> MetricValue:
        """收集内存使用率"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            value = mem.percent
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="memory_percent",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_memory_used(self) -> MetricValue:
        """收集已用内存"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            value = mem.used / (1024 * 1024)  # MB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="memory_used_mb",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="MB"
        )
    
    def _collect_memory_available(self) -> MetricValue:
        """收集可用内存"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            value = mem.available / (1024 * 1024)  # MB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="memory_available_mb",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="MB"
        )
    
    def _collect_disk(self) -> MetricValue:
        """收集磁盘使用率"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            value = (disk.used / disk.total) * 100
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="disk_percent",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="percent"
        )
    
    def _collect_disk_used(self) -> MetricValue:
        """收集已用磁盘空间"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            value = disk.used / (1024 * 1024 * 1024)  # GB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="disk_used_gb",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="GB"
        )
    
    def _collect_disk_free(self) -> MetricValue:
        """收集可用磁盘空间"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            value = disk.free / (1024 * 1024 * 1024)  # GB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="disk_free_gb",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="GB"
        )
    
    def _collect_net_sent(self) -> MetricValue:
        """收集网络发送量"""
        try:
            import psutil
            net = psutil.net_io_counters()
            value = net.bytes_sent / (1024 * 1024)  # MB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="net_io_sent_mb",
            value=value,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            unit="MB"
        )
    
    def _collect_net_recv(self) -> MetricValue:
        """收集网络接收量"""
        try:
            import psutil
            net = psutil.net_io_counters()
            value = net.bytes_recv / (1024 * 1024)  # MB
        except ImportError:
            value = 0.0
        
        return MetricValue(
            name="net_io_recv_mb",
            value=value,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            unit="MB"
        )
    
    def _collect_process_count(self) -> MetricValue:
        """收集进程数量"""
        try:
            import psutil
            value = len(psutil.pids())
        except ImportError:
            value = 0
        
        return MetricValue(
            name="process_count",
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            unit="count"
        )
    
    def get_resource_summary(self) -> dict:
        """获取资源摘要"""
        try:
            import psutil
            
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory': {
                    'percent': mem.percent,
                    'used_mb': mem.used / (1024 * 1024),
                    'available_mb': mem.available / (1024 * 1024),
                    'total_mb': mem.total / (1024 * 1024)
                },
                'disk': {
                    'percent': (disk.used / disk.total) * 100,
                    'used_gb': disk.used / (1024 * 1024 * 1024),
                    'free_gb': disk.free / (1024 * 1024 * 1024),
                    'total_gb': disk.total / (1024 * 1024 * 1024)
                },
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except ImportError:
            return {'error': 'psutil not installed'}
