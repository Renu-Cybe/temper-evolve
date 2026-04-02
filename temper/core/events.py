"""
事件系统 - 模块间通信的基础设施

遵循铁三角原则：
- 信任：所有事件可审计
- 复利：事件历史可查询
- 杠杆：事件处理器可配置

使用示例：
    # 订阅事件
    def on_health_check(event: Event):
        print(f"Health check: {event.data}")
    
    event_bus.subscribe(EventType.HEALTH_CHECK, on_health_check)
    
    # 发布事件
    event = Event(
        type=EventType.HEALTH_CHECK,
        source="monitor",
        data={'status': 'ok'}
    )
    event_bus.publish(event)
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import threading
from queue import Queue, Empty
import uuid


class EventType(Enum):
    """事件类型枚举
    
    按模块分类的事件类型，便于订阅和处理
    """
    # 系统事件
    SYSTEM_START = auto()
    SYSTEM_STOP = auto()
    SYSTEM_ERROR = auto()
    SYSTEM_CONFIG_CHANGED = auto()
    
    # 自感知事件
    HEALTH_CHECK = auto()
    HEALTH_STATUS_CHANGED = auto()
    METRIC_COLLECTED = auto()
    ALERT_TRIGGERED = auto()
    RESOURCE_WARNING = auto()
    
    # 自适应事件
    PARAMETER_TUNED = auto()
    OPTIMIZATION_APPLIED = auto()
    LOAD_BALANCED = auto()
    STRATEGY_TRIGGERED = auto()
    
    # 自组织事件
    WORKFLOW_CREATED = auto()
    WORKFLOW_STARTED = auto()
    WORKFLOW_COMPLETED = auto()
    WORKFLOW_FAILED = auto()
    TASK_SCHEDULED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    DEPENDENCY_RESOLVED = auto()
    
    # 自编译事件
    CODE_GENERATED = auto()
    CODE_REPAIRED = auto()
    HOTLOAD_COMPLETED = auto()
    VALIDATION_PASSED = auto()
    VALIDATION_FAILED = auto()
    
    # 用户事件
    USER_INPUT = auto()
    USER_COMMAND = auto()
    USER_ACTION = auto()


@dataclass
class Event:
    """事件对象
    
    Attributes:
        type: 事件类型
        source: 事件来源模块名称
        timestamp: 事件发生时间
        data: 事件数据（字典格式）
        correlation_id: 关联ID，用于追踪相关事件
        priority: 事件优先级（0-10，数字越小优先级越高）
    """
    type: EventType
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    priority: int = 5
    
    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())[:8]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'type': self.type.name,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'correlation_id': self.correlation_id,
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """从字典创建事件"""
        return cls(
            type=EventType[data['type']],
            source=data['source'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=data.get('data', {}),
            correlation_id=data.get('correlation_id'),
            priority=data.get('priority', 5)
        )


class EventBus:
    """事件总线 - 中心化事件管理
    
    提供异步事件发布和订阅功能，支持多线程安全
    
    使用示例：
        bus = EventBus()
        bus.start()
        
        # 订阅
        bus.subscribe(EventType.SYSTEM_START, lambda e: print("Started!"))
        
        # 发布
        bus.publish(Event(EventType.SYSTEM_START, "main"))
        
        bus.stop()
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self._handlers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()
        self._event_queue: Queue = Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._dropped_count = 0
        self._processed_count = 0
    
    def subscribe(self, event_type: EventType, 
                  handler: Callable[[Event], None]) -> None:
        """订阅事件
        
        Args:
            event_type: 要订阅的事件类型
            handler: 事件处理器函数
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType,
                    handler: Callable[[Event], None]) -> bool:
        """取消订阅
        
        Args:
            event_type: 事件类型
            handler: 要移除的处理器
            
        Returns:
            是否成功移除
        """
        with self._lock:
            if event_type in self._handlers:
                if handler in self._handlers[event_type]:
                    self._handlers[event_type].remove(handler)
                    return True
        return False
    
    def publish(self, event: Event) -> bool:
        """发布事件（异步）
        
        Args:
            event: 要发布的事件
            
        Returns:
            是否成功加入队列
        """
        try:
            self._event_queue.put(event, block=False)
            return True
        except Exception:
            self._dropped_count += 1
            return False
    
    def publish_sync(self, event: Event) -> List[Any]:
        """同步发布事件（立即处理）
        
        Args:
            event: 要发布的事件
            
        Returns:
            所有处理器的结果列表
        """
        handlers = []
        with self._lock:
            handlers = self._handlers.get(event.type, []).copy()
        
        results = []
        for handler in handlers:
            try:
                result = handler(event)
                results.append(result)
            except Exception as e:
                # 记录错误但不中断其他处理器
                print(f"Event handler error for {event.type.name}: {e}")
        
        self._processed_count += 1
        return results
    
    def start(self) -> None:
        """启动事件处理循环"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._process_loop, name="EventBus")
        self._worker_thread.daemon = True
        self._worker_thread.start()
    
    def stop(self, timeout: float = 5.0) -> None:
        """停止事件处理循环
        
        Args:
            timeout: 等待超时时间（秒）
        """
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'processed': self._processed_count,
            'dropped': self._dropped_count,
            'queue_size': self._event_queue.qsize(),
            'running': self._running
        }
    
    def _process_loop(self) -> None:
        """事件处理循环"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.5)
                self.publish_sync(event)
            except Empty:
                continue
            except Exception as e:
                print(f"Event processing error: {e}")


# 全局事件总线实例
event_bus = EventBus()
