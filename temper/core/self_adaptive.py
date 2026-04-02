# -*- coding: utf-8 -*-
"""
自适应模块 (Self-Adaptive Module)

功能：
1. 动态参数调整：根据负载自动调整参数
2. 性能优化：基于指标自动优化配置
3. 限流控制：实现请求限流和熔断
4. 配置热更新：支持运行时更新配置

编码规范：Codong风格
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 提取成功值
- 使用 is_error() 检查错误
"""

import threading
import time
import json
import os
from collections import deque
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# Codong风格工具函数
# =============================================================================

def is_error(result: Dict[str, Any]) -> bool:
    """
    检查结果是否为错误
    
    Args:
        result: 函数返回的结果字典
        
    Returns:
        如果是错误返回True，否则返回False
    """
    return not result.get("ok", False)


def unwrap(result: Dict[str, Any]) -> Any:
    """
    从结果中提取值，如果是错误则抛出异常
    
    Args:
        result: 函数返回的结果字典
        
    Returns:
        成功时的value值
        
    Raises:
        RuntimeError: 如果结果是错误
    """
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def ok(value: Any = None) -> Dict[str, Any]:
    """
    创建成功响应
    
    Args:
        value: 返回值
        
    Returns:
        成功响应字典
    """
    return {"ok": True, "value": value}


def err(error_code: str, message: str) -> Dict[str, Any]:
    """
    创建错误响应
    
    Args:
        error_code: 错误代码
        message: 错误消息
        
    Returns:
        错误响应字典
    """
    return {"ok": False, "error": error_code, "message": message}


# =============================================================================
# 数据类和枚举
# =============================================================================

class AdaptationStrategy(Enum):
    """自适应策略枚举"""
    CONSERVATIVE = "conservative"  # 保守策略：缓慢调整
    AGGRESSIVE = "aggressive"      # 激进策略：快速调整
    BALANCED = "balanced"          # 平衡策略：适中调整


class CircuitState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"      # 关闭状态：正常通过
    OPEN = "open"          # 打开状态：拒绝请求
    HALF_OPEN = "half_open"  # 半开状态：试探性通过


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float = field(default_factory=time.time)
    response_time: float = 0.0      # 响应时间（毫秒）
    throughput: float = 0.0         # 吞吐量（请求/秒）
    error_rate: float = 0.0         # 错误率（0-1）
    cpu_usage: float = 0.0          # CPU使用率（0-1）
    memory_usage: float = 0.0       # 内存使用率（0-1）
    queue_size: int = 0             # 队列大小
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "response_time": self.response_time,
            "throughput": self.throughput,
            "error_rate": self.error_rate,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "queue_size": self.queue_size
        }


@dataclass
class TuningConfig:
    """参数调优配置"""
    min_value: float = 0.0
    max_value: float = 100.0
    step_size: float = 1.0
    target_metric: str = "response_time"
    target_value: float = 100.0     # 目标值
    tolerance: float = 0.1          # 容差范围


@dataclass
class RateLimitConfig:
    """限流配置"""
    max_requests: int = 100         # 最大请求数
    window_size: float = 1.0        # 时间窗口（秒）
    burst_size: int = 10            # 突发请求数


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5      # 失败阈值
    success_threshold: int = 3      # 成功阈值
    timeout: float = 30.0           # 超时时间（秒）
    half_open_max_calls: int = 3    # 半开状态最大调用数


# =============================================================================
# ParameterTuner 类 - 参数调优
# =============================================================================

class ParameterTuner:
    """
    参数调优器
    
    根据性能指标自动调整系统参数，支持多种自适应策略。
    
    特性：
    - 支持保守、激进、平衡三种策略
    - 基于历史数据进行趋势分析
    - 自动参数边界检查
    - 线程安全
    
    示例：
        tuner = ParameterTuner()
        tuner.register_parameter("thread_pool_size", 10, TuningConfig(
            min_value=5, max_value=50, step_size=2
        ))
        result = tuner.adjust_parameter("thread_pool_size", metrics)
    """
    
    def __init__(self, strategy: AdaptationStrategy = AdaptationStrategy.BALANCED):
        """
        初始化参数调优器
        
        Args:
            strategy: 自适应策略，默认为BALANCED
        """
        self._strategy = strategy
        self._parameters: Dict[str, Dict[str, Any]] = {}
        self._history: Dict[str, deque] = {}
        self._lock = threading.RLock()
        
        # 策略对应的调整系数
        self._strategy_multipliers = {
            AdaptationStrategy.CONSERVATIVE: 0.5,
            AdaptationStrategy.BALANCED: 1.0,
            AdaptationStrategy.AGGRESSIVE: 2.0
        }
    
    def register_parameter(
        self, 
        name: str, 
        initial_value: float, 
        config: TuningConfig
    ) -> Dict[str, Any]:
        """
        注册可调优参数
        
        Args:
            name: 参数名称
            initial_value: 初始值
            config: 调优配置
            
        Returns:
            成功返回 {"ok": True, "value": None}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if name in self._parameters:
                return err("PARAM_EXISTS", f"参数 '{name}' 已存在")
            
            # 验证初始值在范围内
            if not (config.min_value <= initial_value <= config.max_value):
                return err(
                    "INVALID_VALUE", 
                    f"初始值 {initial_value} 不在范围 [{config.min_value}, {config.max_value}] 内"
                )
            
            self._parameters[name] = {
                "value": initial_value,
                "config": config,
                "last_adjustment": time.time(),
                "adjustment_count": 0
            }
            self._history[name] = deque(maxlen=100)
            
            return ok(None)
    
    def unregister_parameter(self, name: str) -> Dict[str, Any]:
        """
        注销参数
        
        Args:
            name: 参数名称
            
        Returns:
            成功返回 {"ok": True, "value": None}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if name not in self._parameters:
                return err("PARAM_NOT_FOUND", f"参数 '{name}' 不存在")
            
            del self._parameters[name]
            del self._history[name]
            
            return ok(None)
    
    def get_parameter(self, name: str) -> Dict[str, Any]:
        """
        获取参数当前值
        
        Args:
            name: 参数名称
            
        Returns:
            成功返回 {"ok": True, "value": 当前值}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if name not in self._parameters:
                return err("PARAM_NOT_FOUND", f"参数 '{name}' 不存在")
            
            return ok(self._parameters[name]["value"])
    
    def adjust_parameter(
        self, 
        name: str, 
        metrics: PerformanceMetrics
    ) -> Dict[str, Any]:
        """
        根据性能指标调整参数
        
        Args:
            name: 参数名称
            metrics: 性能指标
            
        Returns:
            成功返回 {"ok": True, "value": 新值}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if name not in self._parameters:
                return err("PARAM_NOT_FOUND", f"参数 '{name}' 不存在")
            
            param = self._parameters[name]
            config = param["config"]
            current_value = param["value"]
            
            # 记录历史
            self._history[name].append({
                "timestamp": time.time(),
                "value": current_value,
                "metrics": metrics.to_dict()
            })
            
            # 获取当前指标值
            current_metric = getattr(metrics, config.target_metric, None)
            if current_metric is None:
                return err("INVALID_METRIC", f"指标 '{config.target_metric}' 不存在")
            
            # 计算调整方向
            diff = config.target_value - current_metric
            
            # 如果在容差范围内，不调整
            if abs(diff) <= config.target_value * config.tolerance:
                return ok(current_value)
            
            # 计算调整步长
            multiplier = self._strategy_multipliers.get(self._strategy, 1.0)
            step = config.step_size * multiplier
            
            # 根据差异调整步长
            if abs(diff) > config.target_value * 0.5:
                step *= 2  # 差异大时加倍调整
            
            # 确定调整方向
            if diff > 0:
                # 需要增加指标值，根据参数特性决定增减
                new_value = current_value + step
            else:
                new_value = current_value - step
            
            # 边界检查
            new_value = max(config.min_value, min(config.max_value, new_value))
            
            # 更新参数
            param["value"] = new_value
            param["last_adjustment"] = time.time()
            param["adjustment_count"] += 1
            
            return ok(new_value)
    
    def set_strategy(self, strategy: AdaptationStrategy) -> Dict[str, Any]:
        """
        设置自适应策略
        
        Args:
            strategy: 新策略
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._strategy = strategy
            return ok(None)
    
    def get_history(self, name: str, limit: int = 10) -> Dict[str, Any]:
        """
        获取参数调整历史
        
        Args:
            name: 参数名称
            limit: 返回记录数限制
            
        Returns:
            成功返回 {"ok": True, "value": 历史记录列表}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if name not in self._history:
                return err("PARAM_NOT_FOUND", f"参数 '{name}' 不存在")
            
            history_list = list(self._history[name])[-limit:]
            return ok(history_list)
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """
        获取所有参数信息
        
        Returns:
            {"ok": True, "value": 参数字典}
        """
        with self._lock:
            result = {}
            for name, param in self._parameters.items():
                result[name] = {
                    "value": param["value"],
                    "adjustment_count": param["adjustment_count"],
                    "last_adjustment": param["last_adjustment"]
                }
            return ok(result)


# =============================================================================
# PerformanceOptimizer 类 - 性能优化
# =============================================================================

class PerformanceOptimizer:
    """
    性能优化器
    
    基于性能指标自动优化系统配置，实现智能调优。
    
    特性：
    - 多维度性能指标收集
    - 趋势分析和预测
    - 自动优化建议生成
    - 优化效果追踪
    
    示例：
        optimizer = PerformanceOptimizer()
        optimizer.record_metrics(metrics)
        suggestions = optimizer.generate_suggestions()
    """
    
    def __init__(self, history_size: int = 1000):
        """
        初始化性能优化器
        
        Args:
            history_size: 历史记录最大数量
        """
        self._metrics_history: deque = deque(maxlen=history_size)
        self._optimization_rules: List[Dict[str, Any]] = []
        self._applied_optimizations: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        
        # 初始化默认优化规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认优化规则"""
        default_rules = [
            {
                "name": "high_response_time",
                "condition": lambda m: m.response_time > 500,
                "action": "increase_resources",
                "priority": 1,
                "description": "响应时间过长，建议增加资源"
            },
            {
                "name": "high_error_rate",
                "condition": lambda m: m.error_rate > 0.1,
                "action": "circuit_breaker",
                "priority": 0,
                "description": "错误率过高，建议启用熔断"
            },
            {
                "name": "high_cpu_usage",
                "condition": lambda m: m.cpu_usage > 0.8,
                "action": "scale_out",
                "priority": 2,
                "description": "CPU使用率过高，建议扩容"
            },
            {
                "name": "high_memory_usage",
                "condition": lambda m: m.memory_usage > 0.85,
                "action": "memory_optimize",
                "priority": 1,
                "description": "内存使用率过高，建议优化内存"
            },
            {
                "name": "low_throughput",
                "condition": lambda m: m.throughput < 10,
                "action": "bottleneck_analysis",
                "priority": 3,
                "description": "吞吐量过低，建议进行瓶颈分析"
            }
        ]
        
        for rule in default_rules:
            self.add_optimization_rule(
                rule["name"],
                rule["condition"],
                rule["action"],
                rule["priority"],
                rule["description"]
            )
    
    def record_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """
        记录性能指标
        
        Args:
            metrics: 性能指标
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._metrics_history.append(metrics)
            return ok(None)
    
    def add_optimization_rule(
        self,
        name: str,
        condition: Callable[[PerformanceMetrics], bool],
        action: str,
        priority: int = 5,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        添加优化规则
        
        Args:
            name: 规则名称
            condition: 条件函数，接收PerformanceMetrics返回bool
            action: 建议动作
            priority: 优先级（数字越小优先级越高）
            description: 规则描述
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            # 检查规则名是否已存在
            for rule in self._optimization_rules:
                if rule["name"] == name:
                    return err("RULE_EXISTS", f"规则 '{name}' 已存在")
            
            self._optimization_rules.append({
                "name": name,
                "condition": condition,
                "action": action,
                "priority": priority,
                "description": description,
                "created_at": time.time()
            })
            
            # 按优先级排序
            self._optimization_rules.sort(key=lambda r: r["priority"])
            
            return ok(None)
    
    def remove_optimization_rule(self, name: str) -> Dict[str, Any]:
        """
        移除优化规则
        
        Args:
            name: 规则名称
            
        Returns:
            成功返回 {"ok": True, "value": None}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            for i, rule in enumerate(self._optimization_rules):
                if rule["name"] == name:
                    del self._optimization_rules[i]
                    return ok(None)
            
            return err("RULE_NOT_FOUND", f"规则 '{name}' 不存在")
    
    def generate_suggestions(self) -> Dict[str, Any]:
        """
        生成优化建议
        
        Returns:
            成功返回 {"ok": True, "value": 建议列表}
        """
        with self._lock:
            if not self._metrics_history:
                return ok([])
            
            # 获取最新指标
            latest_metrics = self._metrics_history[-1]
            
            suggestions = []
            for rule in self._optimization_rules:
                try:
                    if rule["condition"](latest_metrics):
                        suggestions.append({
                            "rule": rule["name"],
                            "action": rule["action"],
                            "priority": rule["priority"],
                            "description": rule["description"],
                            "metrics": latest_metrics.to_dict()
                        })
                except Exception as e:
                    # 条件函数执行失败，跳过此规则
                    continue
            
            return ok(suggestions)
    
    def analyze_trends(self, window_size: int = 10) -> Dict[str, Any]:
        """
        分析性能趋势
        
        Args:
            window_size: 分析窗口大小
            
        Returns:
            成功返回 {"ok": True, "value": 趋势分析结果}
        """
        with self._lock:
            if len(self._metrics_history) < window_size:
                return err(
                    "INSUFFICIENT_DATA", 
                    f"历史数据不足，需要至少 {window_size} 条记录"
                )
            
            # 获取最近的数据
            recent = list(self._metrics_history)[-window_size:]
            
            # 计算各项指标的趋势
            def calc_trend(values: List[float]) -> str:
                """计算趋势方向"""
                if len(values) < 2:
                    return "stable"
                
                first_half = sum(values[:len(values)//2]) / (len(values)//2)
                second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                
                diff_ratio = (second_half - first_half) / first_half if first_half != 0 else 0
                
                if diff_ratio > 0.1:
                    return "increasing"
                elif diff_ratio < -0.1:
                    return "decreasing"
                return "stable"
            
            trends = {
                "response_time": calc_trend([m.response_time for m in recent]),
                "throughput": calc_trend([m.throughput for m in recent]),
                "error_rate": calc_trend([m.error_rate for m in recent]),
                "cpu_usage": calc_trend([m.cpu_usage for m in recent]),
                "memory_usage": calc_trend([m.memory_usage for m in recent])
            }
            
            # 计算平均值
            averages = {
                "response_time": sum(m.response_time for m in recent) / len(recent),
                "throughput": sum(m.throughput for m in recent) / len(recent),
                "error_rate": sum(m.error_rate for m in recent) / len(recent),
                "cpu_usage": sum(m.cpu_usage for m in recent) / len(recent),
                "memory_usage": sum(m.memory_usage for m in recent) / len(recent)
            }
            
            result = {
                "trends": trends,
                "averages": averages,
                "window_size": window_size,
                "analysis_time": time.time()
            }
            
            return ok(result)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        获取指标摘要
        
        Returns:
            成功返回 {"ok": True, "value": 指标摘要}
        """
        with self._lock:
            if not self._metrics_history:
                return ok({
                    "count": 0,
                    "time_range": None,
                    "metrics": {}
                })
            
            metrics_list = list(self._metrics_history)
            
            def calc_stats(values: List[float]) -> Dict[str, float]:
                """计算统计信息"""
                if not values:
                    return {}
                sorted_values = sorted(values)
                return {
                    "min": sorted_values[0],
                    "max": sorted_values[-1],
                    "avg": sum(values) / len(values),
                    "p50": sorted_values[len(sorted_values)//2],
                    "p95": sorted_values[int(len(sorted_values)*0.95)] if len(sorted_values) > 20 else sorted_values[-1],
                    "p99": sorted_values[int(len(sorted_values)*0.99)] if len(sorted_values) > 100 else sorted_values[-1]
                }
            
            summary = {
                "count": len(metrics_list),
                "time_range": {
                    "start": metrics_list[0].timestamp,
                    "end": metrics_list[-1].timestamp
                },
                "metrics": {
                    "response_time": calc_stats([m.response_time for m in metrics_list]),
                    "throughput": calc_stats([m.throughput for m in metrics_list]),
                    "error_rate": calc_stats([m.error_rate for m in metrics_list]),
                    "cpu_usage": calc_stats([m.cpu_usage for m in metrics_list]),
                    "memory_usage": calc_stats([m.memory_usage for m in metrics_list])
                }
            }
            
            return ok(summary)
    
    def apply_optimization(
        self, 
        suggestion: Dict[str, Any], 
        executor: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        应用优化建议
        
        Args:
            suggestion: 优化建议
            executor: 可选的执行函数
            
        Returns:
            成功返回 {"ok": True, "value": 执行结果}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            optimization_record = {
                "suggestion": suggestion,
                "applied_at": time.time(),
                "status": "pending"
            }
            
            try:
                if executor:
                    result = executor(suggestion)
                    optimization_record["status"] = "success"
                    optimization_record["result"] = result
                else:
                    # 默认执行逻辑
                    optimization_record["status"] = "manual_required"
                    optimization_record["message"] = "需要手动执行优化"
                
                self._applied_optimizations.append(optimization_record)
                return ok(optimization_record)
                
            except Exception as e:
                optimization_record["status"] = "failed"
                optimization_record["error"] = str(e)
                self._applied_optimizations.append(optimization_record)
                return err("OPTIMIZATION_FAILED", str(e))


# =============================================================================
# RateLimiter 类 - 限流控制
# =============================================================================

class RateLimiter:
    """
    限流控制器
    
    实现多种限流算法和熔断机制，保护系统免受过载。
    
    特性：
    - 令牌桶算法限流
    - 滑动窗口计数
    - 熔断器模式
    - 自适应限流
    
    示例：
        limiter = RateLimiter()
        limiter.configure_limit("api", RateLimitConfig(max_requests=100))
        
        result = limiter.allow_request("api")
        if unwrap(result):
            # 处理请求
            pass
    """
    
    def __init__(self):
        """初始化限流控制器"""
        # 限流配置
        self._limit_configs: Dict[str, RateLimitConfig] = {}
        
        # 令牌桶状态
        self._token_buckets: Dict[str, Dict[str, Any]] = {}
        
        # 滑动窗口计数
        self._sliding_windows: Dict[str, deque] = {}
        
        # 熔断器状态
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._circuit_configs: Dict[str, CircuitBreakerConfig] = {}
        
        self._lock = threading.RLock()
    
    def configure_limit(self, key: str, config: RateLimitConfig) -> Dict[str, Any]:
        """
        配置限流规则
        
        Args:
            key: 限流键
            config: 限流配置
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._limit_configs[key] = config
            
            # 初始化令牌桶
            self._token_buckets[key] = {
                "tokens": config.burst_size,
                "last_update": time.time()
            }
            
            # 初始化滑动窗口
            self._sliding_windows[key] = deque()
            
            return ok(None)
    
    def configure_circuit_breaker(
        self, 
        key: str, 
        config: CircuitBreakerConfig
    ) -> Dict[str, Any]:
        """
        配置熔断器
        
        Args:
            key: 熔断键
            config: 熔断配置
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._circuit_configs[key] = config
            
            # 初始化熔断器状态
            self._circuit_breakers[key] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0,
                "half_open_calls": 0,
                "total_requests": 0,
                "total_failures": 0
            }
            
            return ok(None)
    
    def _update_tokens(self, key: str):
        """更新令牌桶中的令牌数"""
        bucket = self._token_buckets[key]
        config = self._limit_configs[key]
        
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        # 计算新增的令牌
        tokens_to_add = elapsed * config.max_requests / config.window_size
        bucket["tokens"] = min(config.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now
    
    def _clean_window(self, key: str):
        """清理滑动窗口中的过期记录"""
        window = self._sliding_windows[key]
        config = self._limit_configs[key]
        
        now = time.time()
        cutoff = now - config.window_size
        
        # 移除过期记录
        while window and window[0] < cutoff:
            window.popleft()
    
    def allow_request(self, key: str) -> Dict[str, Any]:
        """
        检查是否允许请求通过
        
        Args:
            key: 限流键
            
        Returns:
            成功返回 {"ok": True, "value": True/False}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            # 检查熔断器
            if key in self._circuit_breakers:
                cb_result = self._check_circuit_breaker(key)
                if is_error(cb_result):
                    return cb_result
                if not unwrap(cb_result):
                    return ok(False)
            
            # 检查限流
            if key not in self._limit_configs:
                return ok(True)  # 未配置限流，允许通过
            
            # 更新令牌桶
            self._update_tokens(key)
            
            # 清理滑动窗口
            self._clean_window(key)
            
            bucket = self._token_buckets[key]
            window = self._sliding_windows[key]
            config = self._limit_configs[key]
            
            # 检查令牌桶
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                window.append(time.time())
                
                # 更新熔断器统计
                if key in self._circuit_breakers:
                    self._circuit_breakers[key]["total_requests"] += 1
                
                return ok(True)
            
            # 检查滑动窗口
            if len(window) < config.max_requests:
                window.append(time.time())
                
                if key in self._circuit_breakers:
                    self._circuit_breakers[key]["total_requests"] += 1
                
                return ok(True)
            
            return ok(False)
    
    def _check_circuit_breaker(self, key: str) -> Dict[str, Any]:
        """检查熔断器状态"""
        cb = self._circuit_breakers[key]
        config = self._circuit_configs[key]
        
        if cb["state"] == CircuitState.OPEN:
            # 检查是否超过超时时间
            if time.time() - cb["last_failure_time"] > config.timeout:
                cb["state"] = CircuitState.HALF_OPEN
                cb["half_open_calls"] = 0
                cb["success_count"] = 0
            else:
                return ok(False)
        
        if cb["state"] == CircuitState.HALF_OPEN:
            if cb["half_open_calls"] >= config.half_open_max_calls:
                return ok(False)
            cb["half_open_calls"] += 1
        
        return ok(True)
    
    def record_success(self, key: str) -> Dict[str, Any]:
        """
        记录请求成功
        
        Args:
            key: 熔断键
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if key not in self._circuit_breakers:
                return ok(None)
            
            cb = self._circuit_breakers[key]
            
            if cb["state"] == CircuitState.HALF_OPEN:
                cb["success_count"] += 1
                
                # 检查是否可以关闭熔断器
                if cb["success_count"] >= self._circuit_configs[key].success_threshold:
                    cb["state"] = CircuitState.CLOSED
                    cb["failure_count"] = 0
                    cb["half_open_calls"] = 0
            
            return ok(None)
    
    def record_failure(self, key: str) -> Dict[str, Any]:
        """
        记录请求失败
        
        Args:
            key: 熔断键
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if key not in self._circuit_breakers:
                return ok(None)
            
            cb = self._circuit_breakers[key]
            config = self._circuit_configs[key]
            
            cb["failure_count"] += 1
            cb["total_failures"] += 1
            cb["last_failure_time"] = time.time()
            
            if cb["state"] == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新打开熔断器
                cb["state"] = CircuitState.OPEN
            elif cb["state"] == CircuitState.CLOSED:
                # 检查是否达到失败阈值
                if cb["failure_count"] >= config.failure_threshold:
                    cb["state"] = CircuitState.OPEN
            
            return ok(None)
    
    def get_circuit_state(self, key: str) -> Dict[str, Any]:
        """
        获取熔断器状态
        
        Args:
            key: 熔断键
            
        Returns:
            成功返回 {"ok": True, "value": 状态信息}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._circuit_breakers:
                return err("CIRCUIT_NOT_FOUND", f"熔断器 '{key}' 不存在")
            
            cb = self._circuit_breakers[key]
            config = self._circuit_configs.get(key)
            
            result = {
                "state": cb["state"].value,
                "failure_count": cb["failure_count"],
                "success_count": cb["success_count"],
                "total_requests": cb["total_requests"],
                "total_failures": cb["total_failures"],
                "last_failure_time": cb["last_failure_time"],
                "failure_rate": cb["total_failures"] / cb["total_requests"] 
                    if cb["total_requests"] > 0 else 0
            }
            
            if config:
                result["config"] = {
                    "failure_threshold": config.failure_threshold,
                    "success_threshold": config.success_threshold,
                    "timeout": config.timeout
                }
            
            return ok(result)
    
    def get_rate_limit_status(self, key: str) -> Dict[str, Any]:
        """
        获取限流状态
        
        Args:
            key: 限流键
            
        Returns:
            成功返回 {"ok": True, "value": 状态信息}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._limit_configs:
                return err("LIMIT_NOT_FOUND", f"限流配置 '{key}' 不存在")
            
            # 更新状态
            self._update_tokens(key)
            self._clean_window(key)
            
            bucket = self._token_buckets[key]
            window = self._sliding_windows[key]
            config = self._limit_configs[key]
            
            result = {
                "tokens_available": bucket["tokens"],
                "tokens_max": config.burst_size,
                "requests_in_window": len(window),
                "window_limit": config.max_requests,
                "window_size": config.window_size
            }
            
            return ok(result)
    
    def reset_circuit(self, key: str) -> Dict[str, Any]:
        """
        手动重置熔断器
        
        Args:
            key: 熔断键
            
        Returns:
            成功返回 {"ok": True, "value": None}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._circuit_breakers:
                return err("CIRCUIT_NOT_FOUND", f"熔断器 '{key}' 不存在")
            
            cb = self._circuit_breakers[key]
            cb["state"] = CircuitState.CLOSED
            cb["failure_count"] = 0
            cb["success_count"] = 0
            cb["half_open_calls"] = 0
            
            return ok(None)


# =============================================================================
# 配置热更新管理器
# =============================================================================

class ConfigHotUpdater:
    """
    配置热更新管理器
    
    支持运行时动态更新配置，无需重启服务。
    
    特性：
    - 配置文件监听
    - 配置版本管理
    - 更新回调机制
    - 配置验证
    
    示例：
        updater = ConfigHotUpdater()
        updater.register_callback("database", on_db_config_change)
        updater.start_watching("/path/to/config.json")
    """
    
    def __init__(self, check_interval: float = 5.0):
        """
        初始化配置热更新管理器
        
        Args:
            check_interval: 配置检查间隔（秒）
        """
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._file_watchers: Dict[str, Dict[str, Any]] = {}
        self._check_interval = check_interval
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._version_counter = 0
    
    def register_callback(self, config_key: str, callback: Callable) -> Dict[str, Any]:
        """
        注册配置更新回调
        
        Args:
            config_key: 配置键
            callback: 回调函数，接收(new_config, old_config)参数
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if config_key not in self._callbacks:
                self._callbacks[config_key] = []
            
            self._callbacks[config_key].append(callback)
            return ok(None)
    
    def unregister_callback(
        self, 
        config_key: str, 
        callback: Callable
    ) -> Dict[str, Any]:
        """
        注销配置更新回调
        
        Args:
            config_key: 配置键
            callback: 回调函数
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if config_key in self._callbacks:
                if callback in self._callbacks[config_key]:
                    self._callbacks[config_key].remove(callback)
            
            return ok(None)
    
    def set_config(self, key: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置配置
        
        Args:
            key: 配置键
            config: 配置字典
            
        Returns:
            成功返回 {"ok": True, "value": 版本号}
        """
        with self._lock:
            old_config = self._configs.get(key, {}).get("data", {})
            
            self._version_counter += 1
            self._configs[key] = {
                "data": config.copy(),
                "version": self._version_counter,
                "updated_at": time.time()
            }
            
            # 触发回调
            self._trigger_callbacks(key, config, old_config)
            
            return ok(self._version_counter)
    
    def get_config(self, key: str) -> Dict[str, Any]:
        """
        获取配置
        
        Args:
            key: 配置键
            
        Returns:
            成功返回 {"ok": True, "value": 配置字典}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._configs:
                return err("CONFIG_NOT_FOUND", f"配置 '{key}' 不存在")
            
            return ok(self._configs[key]["data"])
    
    def update_config(
        self, 
        key: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新配置（合并更新）
        
        Args:
            key: 配置键
            updates: 更新内容
            
        Returns:
            成功返回 {"ok": True, "value": 版本号}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._configs:
                return err("CONFIG_NOT_FOUND", f"配置 '{key}' 不存在")
            
            old_config = self._configs[key]["data"].copy()
            new_config = old_config.copy()
            
            # 递归合并配置
            self._deep_merge(new_config, updates)
            
            self._version_counter += 1
            self._configs[key] = {
                "data": new_config,
                "version": self._version_counter,
                "updated_at": time.time()
            }
            
            # 触发回调
            self._trigger_callbacks(key, new_config, old_config)
            
            return ok(self._version_counter)
    
    def _deep_merge(self, base: Dict, updates: Dict):
        """递归合并字典"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _trigger_callbacks(
        self, 
        key: str, 
        new_config: Dict, 
        old_config: Dict
    ):
        """触发配置更新回调"""
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(new_config, old_config)
                except Exception as e:
                    # 回调执行失败，记录但继续
                    pass
    
    def start_watching(self, file_path: str, config_key: str) -> Dict[str, Any]:
        """
        开始监听配置文件
        
        Args:
            file_path: 配置文件路径
            config_key: 配置键
            
        Returns:
            成功返回 {"ok": True, "value": None}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if not os.path.exists(file_path):
                return err("FILE_NOT_FOUND", f"文件不存在: {file_path}")
            
            try:
                mtime = os.path.getmtime(file_path)
                
                self._file_watchers[file_path] = {
                    "config_key": config_key,
                    "last_mtime": mtime,
                    "file_path": file_path
                }
                
                # 加载初始配置
                result = self._load_config_file(file_path)
                if is_error(result):
                    return result
                
                config = unwrap(result)
                self.set_config(config_key, config)
                
                # 启动监控线程
                if self._watcher_thread is None or not self._watcher_thread.is_alive():
                    self._stop_event.clear()
                    self._watcher_thread = threading.Thread(
                        target=self._watch_loop,
                        daemon=True
                    )
                    self._watcher_thread.start()
                
                return ok(None)
                
            except Exception as e:
                return err("WATCH_FAILED", str(e))
    
    def stop_watching(self, file_path: str) -> Dict[str, Any]:
        """
        停止监听配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if file_path in self._file_watchers:
                del self._file_watchers[file_path]
            
            # 如果没有监听器了，停止线程
            if not self._file_watchers and self._watcher_thread:
                self._stop_event.set()
                self._watcher_thread = None
            
            return ok(None)
    
    def _watch_loop(self):
        """文件监控循环"""
        while not self._stop_event.wait(self._check_interval):
            with self._lock:
                watchers = list(self._file_watchers.items())
            
            for file_path, watcher in watchers:
                try:
                    current_mtime = os.path.getmtime(file_path)
                    
                    if current_mtime > watcher["last_mtime"]:
                        # 文件已修改，重新加载
                        result = self._load_config_file(file_path)
                        if not is_error(result):
                            config = unwrap(result)
                            self.set_config(watcher["config_key"], config)
                        
                        with self._lock:
                            if file_path in self._file_watchers:
                                self._file_watchers[file_path]["last_mtime"] = current_mtime
                
                except Exception:
                    # 文件访问失败，跳过
                    pass
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            config = json.loads(content)
            return ok(config)
            
        except json.JSONDecodeError as e:
            return err("INVALID_JSON", f"JSON解析错误: {str(e)}")
        except Exception as e:
            return err("LOAD_FAILED", f"加载失败: {str(e)}")
    
    def get_config_version(self, key: str) -> Dict[str, Any]:
        """
        获取配置版本信息
        
        Args:
            key: 配置键
            
        Returns:
            成功返回 {"ok": True, "value": 版本信息}
            失败返回 {"ok": False, "error": ..., "message": ...}
        """
        with self._lock:
            if key not in self._configs:
                return err("CONFIG_NOT_FOUND", f"配置 '{key}' 不存在")
            
            info = {
                "version": self._configs[key]["version"],
                "updated_at": self._configs[key]["updated_at"]
            }
            
            return ok(info)


# =============================================================================
# 全局自适应管理器
# =============================================================================

class AdaptiveManager:
    """
    全局自适应管理器
    
    整合参数调优、性能优化、限流控制和配置热更新功能，
    提供统一的自适应管理接口。
    
    示例：
        manager = AdaptiveManager()
        
        # 注册参数
        manager.tuner.register_parameter("threads", 10, TuningConfig())
        
        # 配置限流
        manager.limiter.configure_limit("api", RateLimitConfig())
        
        # 记录性能指标
        manager.record_metrics(metrics)
        
        # 运行自适应循环
        manager.run_adaptation_cycle()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化全局自适应管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        
        # 初始化各个组件
        self.tuner = ParameterTuner()
        self.optimizer = PerformanceOptimizer()
        self.limiter = RateLimiter()
        self.config_updater = ConfigHotUpdater()
        
        # 自适应循环控制
        self._adaptation_interval = 60.0  # 默认60秒
        self._adaptation_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        # 自适应钩子
        self._pre_adaptation_hooks: List[Callable] = []
        self._post_adaptation_hooks: List[Callable] = []
        
        # 内部锁
        self._lock = threading.RLock()
    
    def record_metrics(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """
        记录性能指标
        
        Args:
            metrics: 性能指标
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            result = self.optimizer.record_metrics(metrics)
            return result
    
    def run_adaptation_cycle(self) -> Dict[str, Any]:
        """
        运行一次自适应循环
        
        Returns:
            成功返回 {"ok": True, "value": 调整结果}
        """
        with self._lock:
            results = {
                "parameter_adjustments": {},
                "suggestions": [],
                "timestamp": time.time()
            }
            
            # 执行前置钩子
            for hook in self._pre_adaptation_hooks:
                try:
                    hook()
                except Exception:
                    pass
            
            # 获取最新指标
            summary_result = self.optimizer.get_metrics_summary()
            if is_error(summary_result):
                return summary_result
            
            summary = unwrap(summary_result)
            
            if summary["count"] == 0:
                return err("NO_METRICS", "没有可用的性能指标")
            
            # 构建性能指标对象（使用平均值）
            avg_metrics = summary["metrics"]
            metrics = PerformanceMetrics(
                response_time=avg_metrics.get("response_time", {}).get("avg", 0),
                throughput=avg_metrics.get("throughput", {}).get("avg", 0),
                error_rate=avg_metrics.get("error_rate", {}).get("avg", 0),
                cpu_usage=avg_metrics.get("cpu_usage", {}).get("avg", 0),
                memory_usage=avg_metrics.get("memory_usage", {}).get("avg", 0)
            )
            
            # 调整所有已注册的参数
            params_result = self.tuner.get_all_parameters()
            if not is_error(params_result):
                params = unwrap(params_result)
                for param_name in params.keys():
                    adjust_result = self.tuner.adjust_parameter(param_name, metrics)
                    if not is_error(adjust_result):
                        results["parameter_adjustments"][param_name] = unwrap(adjust_result)
            
            # 生成优化建议
            suggestions_result = self.optimizer.generate_suggestions()
            if not is_error(suggestions_result):
                results["suggestions"] = unwrap(suggestions_result)
            
            # 执行后置钩子
            for hook in self._post_adaptation_hooks:
                try:
                    hook(results)
                except Exception:
                    pass
            
            return ok(results)
    
    def start_auto_adaptation(self, interval: Optional[float] = None) -> Dict[str, Any]:
        """
        启动自动自适应
        
        Args:
            interval: 自适应间隔（秒），默认60秒
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if self._running:
                return err("ALREADY_RUNNING", "自动自适应已在运行")
            
            if interval:
                self._adaptation_interval = interval
            
            self._stop_event.clear()
            self._running = True
            
            self._adaptation_thread = threading.Thread(
                target=self._adaptation_loop,
                daemon=True
            )
            self._adaptation_thread.start()
            
            return ok(None)
    
    def stop_auto_adaptation(self) -> Dict[str, Any]:
        """
        停止自动自适应
        
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            if not self._running:
                return ok(None)
            
            self._stop_event.set()
            self._running = False
            
            if self._adaptation_thread:
                self._adaptation_thread.join(timeout=5.0)
                self._adaptation_thread = None
            
            return ok(None)
    
    def _adaptation_loop(self):
        """自适应循环"""
        while not self._stop_event.wait(self._adaptation_interval):
            try:
                self.run_adaptation_cycle()
            except Exception:
                # 自适应循环出错，继续下一次
                pass
    
    def add_pre_adaptation_hook(self, hook: Callable) -> Dict[str, Any]:
        """
        添加自适应前置钩子
        
        Args:
            hook: 钩子函数
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._pre_adaptation_hooks.append(hook)
            return ok(None)
    
    def add_post_adaptation_hook(self, hook: Callable) -> Dict[str, Any]:
        """
        添加自适应后置钩子
        
        Args:
            hook: 钩子函数
            
        Returns:
            成功返回 {"ok": True, "value": None}
        """
        with self._lock:
            self._post_adaptation_hooks.append(hook)
            return ok(None)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取管理器状态
        
        Returns:
            {"ok": True, "value": 状态信息}
        """
        with self._lock:
            status = {
                "auto_adaptation_running": self._running,
                "adaptation_interval": self._adaptation_interval,
                "pre_hooks_count": len(self._pre_adaptation_hooks),
                "post_hooks_count": len(self._post_adaptation_hooks)
            }
            
            return ok(status)


# =============================================================================
# 便捷函数
# =============================================================================

def create_adaptive_manager() -> AdaptiveManager:
    """
    创建自适应管理器（单例）
    
    Returns:
        AdaptiveManager实例
    """
    return AdaptiveManager()


def get_global_manager() -> AdaptiveManager:
    """
    获取全局自适应管理器
    
    Returns:
        全局AdaptiveManager实例
    """
    return AdaptiveManager()


# =============================================================================
# 模块测试
# =============================================================================

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("自适应模块测试")
    print("=" * 60)
    
    # 测试 ParameterTuner
    print("\n1. 测试 ParameterTuner")
    tuner = ParameterTuner(strategy=AdaptationStrategy.BALANCED)
    
    result = tuner.register_parameter(
        "thread_pool_size", 
        10, 
        TuningConfig(min_value=5, max_value=50, step_size=2, target_metric="response_time", target_value=100)
    )
    print(f"   注册参数: {result}")
    
    metrics = PerformanceMetrics(response_time=150, throughput=50, error_rate=0.01)
    result = tuner.adjust_parameter("thread_pool_size", metrics)
    print(f"   调整参数(响应时间150ms): {result}")
    
    metrics2 = PerformanceMetrics(response_time=80, throughput=60, error_rate=0.01)
    result = tuner.adjust_parameter("thread_pool_size", metrics2)
    print(f"   调整参数(响应时间80ms): {result}")
    
    # 测试 PerformanceOptimizer
    print("\n2. 测试 PerformanceOptimizer")
    optimizer = PerformanceOptimizer()
    
    optimizer.record_metrics(PerformanceMetrics(response_time=200, throughput=30, error_rate=0.05))
    optimizer.record_metrics(PerformanceMetrics(response_time=250, throughput=25, error_rate=0.08))
    optimizer.record_metrics(PerformanceMetrics(response_time=300, throughput=20, error_rate=0.12))
    
    result = optimizer.generate_suggestions()
    print(f"   优化建议: {unwrap(result)}")
    
    result = optimizer.analyze_trends(window_size=3)
    print(f"   趋势分析: {unwrap(result)}")
    
    # 测试 RateLimiter
    print("\n3. 测试 RateLimiter")
    limiter = RateLimiter()
    
    limiter.configure_limit("api", RateLimitConfig(max_requests=5, window_size=1.0, burst_size=3))
    limiter.configure_circuit_breaker("api", CircuitBreakerConfig(failure_threshold=3))
    
    for i in range(7):
        result = limiter.allow_request("api")
        allowed = unwrap(result)
        print(f"   请求 {i+1}: {'通过' if allowed else '拒绝'}")
    
    # 测试熔断器
    print("\n   测试熔断器:")
    for i in range(5):
        limiter.record_failure("api")
    
    result = limiter.get_circuit_state("api")
    print(f"   熔断状态: {unwrap(result)}")
    
    # 测试 ConfigHotUpdater
    print("\n4. 测试 ConfigHotUpdater")
    updater = ConfigHotUpdater()
    
    def on_config_change(new_cfg, old_cfg):
        print(f"   配置已更新: {old_cfg} -> {new_cfg}")
    
    updater.register_callback("app", on_config_change)
    updater.set_config("app", {"db": {"host": "localhost", "port": 3306}})
    updater.update_config("app", {"db": {"port": 3307}})
    
    result = updater.get_config("app")
    print(f"   当前配置: {unwrap(result)}")
    
    # 测试 AdaptiveManager
    print("\n5. 测试 AdaptiveManager")
    manager = get_global_manager()
    
    manager.tuner.register_parameter(
        "cache_size", 
        100, 
        TuningConfig(min_value=50, max_value=500, target_metric="memory_usage", target_value=0.7)
    )
    
    manager.record_metrics(PerformanceMetrics(
        response_time=120, 
        throughput=45, 
        error_rate=0.02,
        cpu_usage=0.6,
        memory_usage=0.8
    ))
    
    result = manager.run_adaptation_cycle()
    print(f"   自适应结果: {result}")
    
    result = manager.get_status()
    print(f"   管理器状态: {unwrap(result)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
