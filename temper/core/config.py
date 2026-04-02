#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统模块 - 杠杆原则

提供统一的配置管理接口，支持配置分层、验证和热加载功能。
遵循Codong风格错误处理规范。

配置文件路径: ~/.temper/config.json
"""

import json
import os
import re
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


# =============================================================================
# Codong风格错误处理工具函数
# =============================================================================

def ok(value: Any) -> Dict[str, Any]:
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


def is_error(result: Dict[str, Any]) -> bool:
    """
    检查结果是否为错误
    
    Args:
        result: 响应结果字典
        
    Returns:
        是否为错误
    """
    return not result.get("ok", False)


def unwrap(result: Dict[str, Any]) -> Any:
    """
    从结果中提取值，如果是错误则抛出异常
    
    Args:
        result: 响应结果字典
        
    Returns:
        成功时的返回值
        
    Raises:
        RuntimeError: 如果结果是错误
    """
    if is_error(result):
        error_code = result.get("error", "UNKNOWN_ERROR")
        message = result.get("message", "未知错误")
        raise RuntimeError(f"[{error_code}] {message}")
    return result.get("value")


def unwrap_or(result: Dict[str, Any], default: Any) -> Any:
    """
    从结果中提取值，如果是错误则返回默认值
    
    Args:
        result: 响应结果字典
        default: 默认值
        
    Returns:
        成功时的返回值或默认值
    """
    if is_error(result):
        return default
    return result.get("value")


# =============================================================================
# 配置验证器
# =============================================================================

class ConfigValidator:
    """
    配置验证器类
    
    提供配置项的类型验证、范围验证和自定义验证功能。
    """
    
    def __init__(self):
        """初始化验证器"""
        # 验证规则注册表: {配置路径: 验证函数列表}
        self._validators: Dict[str, List[Callable[[Any], Dict[str, Any]]]] = {}
        # 类型映射
        self._type_map = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
    
    def register(self, path: str, validator: Callable[[Any], Dict[str, Any]]) -> Dict[str, Any]:
        """
        注册配置验证器
        
        Args:
            path: 配置路径，使用点号分隔（如 "app.name"）
            validator: 验证函数，接收值返回验证结果
            
        Returns:
            操作结果
        """
        if not path or not isinstance(path, str):
            return err("INVALID_PATH", "配置路径必须是非空字符串")
        
        if not callable(validator):
            return err("INVALID_VALIDATOR", "验证器必须是可调用的函数")
        
        if path not in self._validators:
            self._validators[path] = []
        
        self._validators[path].append(validator)
        return ok(None)
    
    def register_type_validator(self, path: str, expected_type: Union[str, type]) -> Dict[str, Any]:
        """
        注册类型验证器
        
        Args:
            path: 配置路径
            expected_type: 期望的类型（字符串名称或类型对象）
            
        Returns:
            操作结果
        """
        if isinstance(expected_type, str):
            type_class = self._type_map.get(expected_type)
            if type_class is None:
                return err("UNKNOWN_TYPE", f"未知类型: {expected_type}")
        else:
            type_class = expected_type
        
        def type_validator(value: Any) -> Dict[str, Any]:
            if value is None:
                return ok(None)  # None值通过类型检查（使用默认值）
            if not isinstance(value, type_class):
                return err(
                    "TYPE_MISMATCH",
                    f"配置项 '{path}' 期望类型 {type_class.__name__}, 实际类型 {type(value).__name__}"
                )
            return ok(None)
        
        return self.register(path, type_validator)
    
    def register_range_validator(
        self, 
        path: str, 
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> Dict[str, Any]:
        """
        注册范围验证器（用于数值类型）
        
        Args:
            path: 配置路径
            min_value: 最小值（包含）
            max_value: 最大值（包含）
            
        Returns:
            操作结果
        """
        def range_validator(value: Any) -> Dict[str, Any]:
            if value is None:
                return ok(None)
            
            if not isinstance(value, (int, float)):
                return err("TYPE_ERROR", f"配置项 '{path}' 必须是数值类型")
            
            if min_value is not None and value < min_value:
                return err(
                    "VALUE_TOO_SMALL",
                    f"配置项 '{path}' 的值 {value} 小于最小值 {min_value}"
                )
            
            if max_value is not None and value > max_value:
                return err(
                    "VALUE_TOO_LARGE",
                    f"配置项 '{path}' 的值 {value} 大于最大值 {max_value}"
                )
            
            return ok(None)
        
        return self.register(path, range_validator)
    
    def register_regex_validator(self, path: str, pattern: str) -> Dict[str, Any]:
        """
        注册正则表达式验证器（用于字符串类型）
        
        Args:
            path: 配置路径
            pattern: 正则表达式模式
            
        Returns:
            操作结果
        """
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            return err("INVALID_PATTERN", f"无效的正则表达式: {e}")
        
        def regex_validator(value: Any) -> Dict[str, Any]:
            if value is None:
                return ok(None)
            
            if not isinstance(value, str):
                return err("TYPE_ERROR", f"配置项 '{path}' 必须是字符串类型")
            
            if not compiled_pattern.match(value):
                return err(
                    "PATTERN_MISMATCH",
                    f"配置项 '{path}' 的值 '{value}' 不匹配模式 '{pattern}'"
                )
            
            return ok(None)
        
        return self.register(path, regex_validator)
    
    def register_enum_validator(self, path: str, allowed_values: List[Any]) -> Dict[str, Any]:
        """
        注册枚举验证器
        
        Args:
            path: 配置路径
            allowed_values: 允许的值列表
            
        Returns:
            操作结果
        """
        allowed_set = set(allowed_values)
        
        def enum_validator(value: Any) -> Dict[str, Any]:
            if value is None:
                return ok(None)
            
            if value not in allowed_set:
                return err(
                    "INVALID_VALUE",
                    f"配置项 '{path}' 的值 '{value}' 不在允许的值列表中: {allowed_values}"
                )
            
            return ok(None)
        
        return self.register(path, enum_validator)
    
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证整个配置
        
        Args:
            config: 配置字典
            
        Returns:
            验证结果，包含所有错误
        """
        errors = []
        
        for path, validators in self._validators.items():
            value = self._get_nested_value(config, path)
            
            for validator in validators:
                result = validator(value)
                if is_error(result):
                    errors.append({
                        "path": path,
                        "error": result.get("error"),
                        "message": result.get("message")
                    })
        
        if errors:
            return err("VALIDATION_FAILED", f"配置验证失败: {errors}")
        
        return ok(None)
    
    def validate_value(self, path: str, value: Any) -> Dict[str, Any]:
        """
        验证单个配置项
        
        Args:
            path: 配置路径
            value: 配置值
            
        Returns:
            验证结果
        """
        validators = self._validators.get(path, [])
        
        for validator in validators:
            result = validator(value)
            if is_error(result):
                return result
        
        return ok(None)
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """
        获取嵌套配置值
        
        Args:
            config: 配置字典
            path: 点号分隔的路径
            
        Returns:
            配置值，如果不存在返回None
        """
        keys = path.split(".")
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current


# =============================================================================
# 默认配置定义
# =============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # 应用程序配置
    "app": {
        "name": "Temper",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    },
    
    # 日志配置
    "logging": {
        "enabled": True,
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "file": {
            "enabled": False,
            "path": "~/.temper/logs/temper.log",
            "max_size_mb": 10,
            "backup_count": 5,
        },
        "console": {
            "enabled": True,
            "color": True,
        },
    },
    
    # 存储配置
    "storage": {
        "base_path": "~/.temper",
        "data_path": "~/.temper/data",
        "cache_path": "~/.temper/cache",
        "temp_path": "~/.temper/temp",
    },
    
    # 网络配置
    "network": {
        "timeout": 30,
        "retry_count": 3,
        "retry_delay": 1.0,
        "user_agent": "Temper/1.0.0",
    },
    
    # 插件配置
    "plugins": {
        "enabled": True,
        "auto_load": True,
        "paths": ["~/.temper/plugins"],
    },
    
    # UI配置
    "ui": {
        "theme": "default",  # default, dark, light
        "language": "zh_CN",
        "interactive": True,
    },
}


# =============================================================================
# 配置管理器
# =============================================================================

class Config:
    """
    配置管理器类
    
    提供统一的配置管理接口，支持配置分层、验证和热加载。
    
    配置分层（优先级从低到高）:
    1. 默认配置 (default)
    2. 用户配置文件 (~/.temper/config.json)
    3. 运行时配置 (runtime)
    
    示例:
        >>> config = Config()
        >>> result = config.load()
        >>> if is_error(result):
        ...     print(result["message"])
        >>> value = unwrap(config.get("app.name"))
        >>> result = config.set("app.debug", True)
    """
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = "~/.temper/config.json"
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        validator: Optional[ConfigValidator] = None
    ):
        """
        初始化配置管理器
        
        Args:
            config_path: 用户配置文件路径，默认为 ~/.temper/config.json
            default_config: 默认配置字典，使用内置默认值如果为None
            validator: 配置验证器，自动创建如果为None
        """
        # 配置路径
        self._config_path = Path(config_path or self.DEFAULT_CONFIG_PATH).expanduser()
        
        # 三层配置存储
        self._default: Dict[str, Any] = deepcopy(default_config or DEFAULT_CONFIG)
        self._user: Dict[str, Any] = {}
        self._runtime: Dict[str, Any] = {}
        
        # 验证器
        self._validator = validator or ConfigValidator()
        
        # 线程锁（用于热加载）
        self._lock = threading.RLock()
        
        # 热加载监视器
        self._watcher: Optional[threading.Thread] = None
        self._watching = False
        self._watch_interval = 1.0  # 秒
        self._last_mtime: Optional[float] = None
        
        # 变更回调
        self._on_change_callbacks: List[Callable[[str, Any, Any], None]] = []
        
        # 初始化默认验证规则
        self._init_default_validators()
    
    def _init_default_validators(self) -> None:
        """初始化默认验证规则"""
        # 应用程序配置验证
        self._validator.register_type_validator("app.name", "string")
        self._validator.register_type_validator("app.version", "string")
        self._validator.register_type_validator("app.debug", "bool")
        self._validator.register_enum_validator(
            "app.log_level", 
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        
        # 日志配置验证
        self._validator.register_type_validator("logging.enabled", "bool")
        self._validator.register_enum_validator(
            "logging.level",
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        )
        self._validator.register_type_validator("logging.file.enabled", "bool")
        self._validator.register_type_validator("logging.file.max_size_mb", "int")
        self._validator.register_range_validator("logging.file.max_size_mb", 1, 1000)
        self._validator.register_type_validator("logging.file.backup_count", "int")
        self._validator.register_range_validator("logging.file.backup_count", 0, 100)
        
        # 网络配置验证
        self._validator.register_type_validator("network.timeout", "int")
        self._validator.register_range_validator("network.timeout", 1, 300)
        self._validator.register_type_validator("network.retry_count", "int")
        self._validator.register_range_validator("network.retry_count", 0, 10)
        self._validator.register_type_validator("network.retry_delay", "float")
        self._validator.register_range_validator("network.retry_delay", 0.0, 60.0)
        
        # 插件配置验证
        self._validator.register_type_validator("plugins.enabled", "bool")
        self._validator.register_type_validator("plugins.auto_load", "bool")
        self._validator.register_type_validator("plugins.paths", "list")
        
        # UI配置验证
        self._validator.register_enum_validator("ui.theme", ["default", "dark", "light"])
        self._validator.register_type_validator("ui.language", "string")
        self._validator.register_type_validator("ui.interactive", "bool")
    
    # ==========================================================================
    # 核心配置操作
    # ==========================================================================
    
    def load(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载用户配置文件
        
        如果配置文件不存在，则创建一个包含默认配置的文件。
        
        Args:
            path: 配置文件路径，使用初始化时设置的路径如果为None
            
        Returns:
            操作结果
        """
        with self._lock:
            config_path = Path(path).expanduser() if path else self._config_path
            
            try:
                # 确保配置目录存在
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 如果配置文件不存在，创建默认配置
                if not config_path.exists():
                    self._user = {}
                    return self.save(config_path)
                
                # 读取配置文件
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self._user = {}
                    else:
                        self._user = json.loads(content)
                
                # 验证配置
                merged = self._merge_config()
                result = self._validator.validate(merged)
                if is_error(result):
                    return result
                
                # 更新最后修改时间
                self._last_mtime = config_path.stat().st_mtime
                
                return ok(None)
                
            except json.JSONDecodeError as e:
                return err("PARSE_ERROR", f"配置文件JSON解析错误: {e}")
            except PermissionError as e:
                return err("PERMISSION_DENIED", f"无法读取配置文件: {e}")
            except Exception as e:
                return err("LOAD_ERROR", f"加载配置文件失败: {e}")
    
    def save(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        保存用户配置到文件
        
        Args:
            path: 配置文件路径，使用初始化时设置的路径如果为None
            
        Returns:
            操作结果
        """
        with self._lock:
            config_path = Path(path).expanduser() if path else self._config_path
            
            try:
                # 确保配置目录存在
                config_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 写入配置文件
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(self._user, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                
                # 更新最后修改时间
                self._last_mtime = config_path.stat().st_mtime
                
                return ok(None)
                
            except PermissionError as e:
                return err("PERMISSION_DENIED", f"无法写入配置文件: {e}")
            except Exception as e:
                return err("SAVE_ERROR", f"保存配置文件失败: {e}")
    
    def get(self, path: Optional[str] = None, default: Any = None) -> Dict[str, Any]:
        """
        获取配置值
        
        按优先级查找：运行时 > 用户配置 > 默认配置
        
        Args:
            path: 配置路径，使用点号分隔。如果为None返回整个配置
            default: 默认值，如果配置项不存在返回此值
            
        Returns:
            包含配置值的结果字典
        """
        with self._lock:
            if path is None:
                return ok(self._merge_config())
            
            # 按优先级查找
            value = self._get_nested_value(self._runtime, path)
            if value is not None:
                return ok(value)
            
            value = self._get_nested_value(self._user, path)
            if value is not None:
                return ok(value)
            
            value = self._get_nested_value(self._default, path)
            if value is not None:
                return ok(value)
            
            return ok(default)
    
    def set(
        self, 
        path: str, 
        value: Any, 
        layer: str = "runtime",
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        设置配置值
        
        Args:
            path: 配置路径，使用点号分隔
            value: 配置值
            layer: 配置层，可选 "user" 或 "runtime"
            validate: 是否验证配置值
            
        Returns:
            操作结果
        """
        with self._lock:
            if layer not in ("user", "runtime"):
                return err("INVALID_LAYER", f"无效的配置层: {layer}，必须是 'user' 或 'runtime'")
            
            # 验证配置值
            if validate:
                result = self._validator.validate_value(path, value)
                if is_error(result):
                    return result
            
            # 获取旧值
            old_value = unwrap_or(self.get(path), None)
            
            # 设置新值
            target = self._user if layer == "user" else self._runtime
            self._set_nested_value(target, path, value)
            
            # 触发变更回调
            self._notify_change(path, old_value, value)
            
            return ok(None)
    
    def delete(self, path: str, layer: str = "runtime") -> Dict[str, Any]:
        """
        删除配置项
        
        Args:
            path: 配置路径
            layer: 配置层，可选 "user" 或 "runtime"
            
        Returns:
            操作结果
        """
        with self._lock:
            if layer not in ("user", "runtime"):
                return err("INVALID_LAYER", f"无效的配置层: {layer}")
            
            target = self._user if layer == "user" else self._runtime
            
            # 获取旧值
            old_value = unwrap_or(self.get(path), None)
            
            # 删除配置项
            if self._delete_nested_value(target, path):
                self._notify_change(path, old_value, None)
                return ok(None)
            
            return err("NOT_FOUND", f"配置项不存在: {path}")
    
    def reset(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        重置配置为默认值
        
        Args:
            path: 配置路径，如果为None重置所有配置
            
        Returns:
            操作结果
        """
        with self._lock:
            if path is None:
                # 重置所有配置
                old_user = self._user
                old_runtime = self._runtime
                self._user = {}
                self._runtime = {}
                
                # 通知所有变更
                for key in set(old_user.keys()) | set(old_runtime.keys()):
                    self._notify_change(key, "...", None)
            else:
                # 获取旧值
                old_value = unwrap_or(self.get(path), None)
                
                # 删除用户层和运行时层的配置
                self._delete_nested_value(self._user, path)
                self._delete_nested_value(self._runtime, path)
                
                # 获取新值（应该是默认值）
                new_value = unwrap_or(self.get(path), None)
                
                self._notify_change(path, old_value, new_value)
            
            return ok(None)
    
    def has(self, path: str) -> Dict[str, Any]:
        """
        检查配置项是否存在
        
        Args:
            path: 配置路径
            
        Returns:
            包含布尔值的结果字典
        """
        with self._lock:
            result = self.get(path)
            if is_error(result):
                return result
            return ok(result.get("value") is not None)
    
    # ==========================================================================
    # 配置分层操作
    # ==========================================================================
    
    def get_layer(self, layer: str) -> Dict[str, Any]:
        """
        获取指定层的配置
        
        Args:
            layer: 配置层，可选 "default", "user", "runtime"
            
        Returns:
            包含配置字典的结果
        """
        with self._lock:
            if layer == "default":
                return ok(deepcopy(self._default))
            elif layer == "user":
                return ok(deepcopy(self._user))
            elif layer == "runtime":
                return ok(deepcopy(self._runtime))
            else:
                return err("INVALID_LAYER", f"无效的配置层: {layer}")
    
    def set_layer(self, layer: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置整个配置层
        
        Args:
            layer: 配置层，可选 "user" 或 "runtime"
            config: 配置字典
            
        Returns:
            操作结果
        """
        with self._lock:
            if layer not in ("user", "runtime"):
                return err("INVALID_LAYER", f"无效的配置层: {layer}")
            
            # 验证配置
            if layer == "user":
                merged = {**self._default, **config, **self._runtime}
            else:
                merged = {**self._default, **self._user, **config}
            
            result = self._validator.validate(merged)
            if is_error(result):
                return result
            
            # 设置配置层
            if layer == "user":
                self._user = deepcopy(config)
            else:
                self._runtime = deepcopy(config)
            
            return ok(None)
    
    def get_merged_config(self) -> Dict[str, Any]:
        """
        获取合并后的配置（运行时 > 用户 > 默认）
        
        Returns:
            合并后的配置字典
        """
        with self._lock:
            return self._merge_config()
    
    def _merge_config(self) -> Dict[str, Any]:
        """
        内部方法：合并三层配置
        
        Returns:
            合并后的配置字典
        """
        return self._deep_merge(self._deep_merge(self._default, self._user), self._runtime)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典
        
        Args:
            base: 基础字典
            override: 覆盖字典
            
        Returns:
            合并后的字典
        """
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        
        return result
    
    # ==========================================================================
    # 热加载功能
    # ==========================================================================
    
    def start_watching(self, interval: Optional[float] = None) -> Dict[str, Any]:
        """
        开始监视配置文件变化
        
        Args:
            interval: 检查间隔（秒），默认1秒
            
        Returns:
            操作结果
        """
        with self._lock:
            if self._watching:
                return err("ALREADY_WATCHING", "已经在监视配置文件")
            
            self._watch_interval = interval or self._watch_interval
            self._watching = True
            
            def watch_loop():
                while self._watching:
                    try:
                        self._check_and_reload()
                    except Exception:
                        pass
                    threading.Event().wait(self._watch_interval)
            
            self._watcher = threading.Thread(target=watch_loop, daemon=True)
            self._watcher.start()
            
            return ok(None)
    
    def stop_watching(self) -> Dict[str, Any]:
        """
        停止监视配置文件变化
        
        Returns:
            操作结果
        """
        with self._lock:
            if not self._watching:
                return err("NOT_WATCHING", "当前没有在监视配置文件")
            
            self._watching = False
            
            if self._watcher:
                self._watcher.join(timeout=self._watch_interval + 0.5)
                self._watcher = None
            
            return ok(None)
    
    def is_watching(self) -> bool:
        """
        检查是否正在监视配置文件
        
        Returns:
            是否正在监视
        """
        return self._watching
    
    def _check_and_reload(self) -> None:
        """内部方法：检查并重新加载配置文件"""
        try:
            if not self._config_path.exists():
                return
            
            current_mtime = self._config_path.stat().st_mtime
            
            if self._last_mtime is None or current_mtime > self._last_mtime:
                # 记录旧配置用于比较
                old_config = self.get_merged_config()
                
                # 重新加载
                result = self.load()
                if not is_error(result):
                    self._last_mtime = current_mtime
                    
                    # 通知变更
                    new_config = self.get_merged_config()
                    self._notify_config_change(old_config, new_config)
                    
        except Exception:
            pass
    
    def reload(self) -> Dict[str, Any]:
        """
        强制重新加载配置文件
        
        Returns:
            操作结果
        """
        with self._lock:
            old_config = self.get_merged_config()
            
            result = self.load()
            if is_error(result):
                return result
            
            new_config = self.get_merged_config()
            self._notify_config_change(old_config, new_config)
            
            return ok(None)
    
    # ==========================================================================
    # 变更通知
    # ==========================================================================
    
    def on_change(self, callback: Callable[[str, Any, Any], None]) -> Dict[str, Any]:
        """
        注册配置变更回调
        
        Args:
            callback: 回调函数，接收 (path, old_value, new_value) 参数
            
        Returns:
            操作结果
        """
        if not callable(callback):
            return err("INVALID_CALLBACK", "回调必须是可调用的函数")
        
        self._on_change_callbacks.append(callback)
        return ok(None)
    
    def remove_on_change(self, callback: Callable[[str, Any, Any], None]) -> Dict[str, Any]:
        """
        移除配置变更回调
        
        Args:
            callback: 要移除的回调函数
            
        Returns:
            操作结果
        """
        try:
            self._on_change_callbacks.remove(callback)
            return ok(None)
        except ValueError:
            return err("CALLBACK_NOT_FOUND", "回调函数未注册")
    
    def _notify_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """
        通知配置项变更
        
        Args:
            path: 配置路径
            old_value: 旧值
            new_value: 新值
        """
        for callback in self._on_change_callbacks:
            try:
                callback(path, old_value, new_value)
            except Exception:
                pass
    
    def _notify_config_change(
        self, 
        old_config: Dict[str, Any], 
        new_config: Dict[str, Any]
    ) -> None:
        """
        通知整个配置变更
        
        Args:
            old_config: 旧配置
            new_config: 新配置
        """
        # 找出所有变更的配置项
        changes = self._find_config_changes(old_config, new_config)
        
        for path, old_val, new_val in changes:
            self._notify_change(path, old_val, new_val)
    
    def _find_config_changes(
        self, 
        old: Dict[str, Any], 
        new: Dict[str, Any],
        prefix: str = ""
    ) -> List[tuple]:
        """
        递归查找配置变更
        
        Args:
            old: 旧配置
            new: 新配置
            prefix: 路径前缀
            
        Returns:
            变更列表 [(path, old_value, new_value), ...]
        """
        changes = []
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            path = f"{prefix}.{key}" if prefix else key
            old_val = old.get(key)
            new_val = new.get(key)
            
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                changes.extend(self._find_config_changes(old_val, new_val, path))
            elif old_val != new_val:
                changes.append((path, old_val, new_val))
        
        return changes
    
    # ==========================================================================
    # 辅助方法
    # ==========================================================================
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """
        获取嵌套配置值
        
        Args:
            config: 配置字典
            path: 点号分隔的路径
            
        Returns:
            配置值，如果不存在返回None
        """
        keys = path.split(".")
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """
        设置嵌套配置值
        
        Args:
            config: 配置字典
            path: 点号分隔的路径
            value: 配置值
        """
        keys = path.split(".")
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _delete_nested_value(self, config: Dict[str, Any], path: str) -> bool:
        """
        删除嵌套配置值
        
        Args:
            config: 配置字典
            path: 点号分隔的路径
            
        Returns:
            是否成功删除
        """
        keys = path.split(".")
        current = config
        
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False
        
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return True
        
        return False
    
    # ==========================================================================
    # 属性访问
    # ==========================================================================
    
    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path
    
    @property
    def validator(self) -> ConfigValidator:
        """获取配置验证器"""
        return self._validator


# =============================================================================
# 全局配置实例
# =============================================================================

# 全局配置实例（单例模式）
_global_config: Optional[Config] = None
_global_config_lock = threading.Lock()


def get_config(
    config_path: Optional[str] = None,
    auto_load: bool = True
) -> Config:
    """
    获取全局配置实例（单例）
    
    Args:
        config_path: 配置文件路径
        auto_load: 是否自动加载配置
        
    Returns:
        全局配置实例
    """
    global _global_config
    
    with _global_config_lock:
        if _global_config is None:
            _global_config = Config(config_path=config_path)
            if auto_load:
                result = _global_config.load()
                if is_error(result):
                    # 如果加载失败，使用默认配置
                    pass
        
        return _global_config


def reset_config() -> None:
    """重置全局配置实例"""
    global _global_config
    
    with _global_config_lock:
        if _global_config and _global_config.is_watching():
            _global_config.stop_watching()
        _global_config = None


# =============================================================================
# 便捷函数
# =============================================================================

def config_get(path: Optional[str] = None, default: Any = None) -> Any:
    """
    便捷函数：获取配置值
    
    Args:
        path: 配置路径
        default: 默认值
        
    Returns:
        配置值
    """
    return unwrap(get_config().get(path, default))


def config_set(path: str, value: Any, layer: str = "runtime") -> Dict[str, Any]:
    """
    便捷函数：设置配置值
    
    Args:
        path: 配置路径
        value: 配置值
        layer: 配置层
        
    Returns:
        操作结果
    """
    return get_config().set(path, value, layer)


def config_save() -> Dict[str, Any]:
    """
    便捷函数：保存配置
    
    Returns:
        操作结果
    """
    return get_config().save()


def config_reload() -> Dict[str, Any]:
    """
    便捷函数：重新加载配置
    
    Returns:
        操作结果
    """
    return get_config().reload()


# =============================================================================
# 模块测试
# =============================================================================

if __name__ == "__main__":
    # 测试配置系统
    print("=" * 60)
    print("配置系统测试")
    print("=" * 60)
    
    # 创建配置实例
    config = Config()
    
    # 测试加载配置
    print("\n1. 加载配置...")
    result = config.load()
    print(f"   结果: {result}")
    
    # 测试获取配置
    print("\n2. 获取配置...")
    result = config.get("app.name")
    print(f"   app.name: {result}")
    
    result = config.get("app.debug")
    print(f"   app.debug: {result}")
    
    # 测试设置配置
    print("\n3. 设置配置...")
    result = config.set("app.debug", True)
    print(f"   设置 app.debug = True: {result}")
    
    result = config.get("app.debug")
    print(f"   app.debug: {result}")
    
    # 测试验证
    print("\n4. 测试验证...")
    result = config.set("network.timeout", 500)  # 超出范围
    print(f"   设置无效值: {result}")
    
    result = config.set("app.log_level", "INVALID")
    print(f"   设置无效枚举值: {result}")
    
    # 测试分层配置
    print("\n5. 测试配置分层...")
    result = config.get_layer("default")
    print(f"   默认层 keys: {list(unwrap(result).keys())}")
    
    result = config.get_layer("user")
    print(f"   用户层: {unwrap(result)}")
    
    result = config.get_layer("runtime")
    print(f"   运行时层: {unwrap(result)}")
    
    # 测试合并配置
    print("\n6. 测试合并配置...")
    merged = config.get_merged_config()
    print(f"   合并后的 app.debug: {merged.get('app', {}).get('debug')}")
    
    # 测试保存配置
    print("\n7. 保存配置...")
    result = config.save()
    print(f"   结果: {result}")
    
    # 测试变更回调
    print("\n8. 测试变更回调...")
    def on_change(path, old_val, new_val):
        print(f"   [回调] {path}: {old_val} -> {new_val}")
    
    config.on_change(on_change)
    config.set("app.name", "TestApp")
    
    # 清理
    config.remove_on_change(on_change)
    config.reset()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
