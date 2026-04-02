"""
配置管理器

负责配置的加载、保存、更新和热重载
"""

import os
import json
from typing import Optional, Any, Callable, List
from pathlib import Path
from .schema import Config, LogLevel
from ..core.result import Result, ok, err, ErrorCode


class ConfigManager:
    """配置管理器
    
    支持分层配置：
    1. 默认配置（代码中定义）
    2. 配置文件（YAML/JSON）
    3. 环境变量（TEMPER_* 前缀）
    4. 运行时更新
    
    使用示例：
        manager = ConfigManager("data/config")
        result = manager.load()
        if is_ok(result):
            config = manager.get()
            print(config.system.log_level)
        
        # 更新配置
        manager.update("system.log_level", "debug")
    """
    
    def __init__(self, config_dir: str = "data/config"):
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file = self._config_dir / "config.yaml"
        self._config: Config = Config()
        self._listeners: List[Callable[[str, Any], None]] = []
        self._watcher = None
    
    def load(self) -> Result[Config, Any]:
        """加载配置
        
        加载顺序：
        1. 默认配置
        2. 配置文件（如果存在）
        3. 环境变量
        
        Returns:
            成功返回配置对象，失败返回错误
        """
        try:
            # 1. 加载默认配置
            config = Config()
            
            # 2. 从文件加载
            if self._config_file.exists():
                file_result = self._load_from_file()
                if is_ok(file_result):
                    config = self._merge_config(config, file_result.value)
            
            # 3. 从环境变量加载
            config = self._load_from_env(config)
            
            self._config = config
            return ok(config)
            
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to load config: {e}")
    
    def _load_from_file(self) -> Result[dict, Any]:
        """从文件加载配置"""
        try:
            suffix = self._config_file.suffix.lower()
            
            with open(self._config_file, 'r', encoding='utf-8') as f:
                if suffix in ['.yaml', '.yml']:
                    try:
                        import yaml
                        return ok(yaml.safe_load(f) or {})
                    except ImportError:
                        return err(ErrorCode.CONFIG_ERROR, "PyYAML not installed")
                elif suffix == '.json':
                    return ok(json.load(f))
                else:
                    # 默认尝试 YAML
                    try:
                        import yaml
                        return ok(yaml.safe_load(f) or {})
                    except ImportError:
                        return err(ErrorCode.CONFIG_ERROR, "PyYAML not installed")
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to read config file: {e}")
    
    def _load_from_env(self, config: Config) -> Config:
        """从环境变量加载配置"""
        prefix = "TEMPER_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # 转换环境变量名到配置路径
                # TEMPER_SYSTEM_LOG_LEVEL -> system.log_level
                path = key[len(prefix):].lower().replace('_', '.')
                
                # 尝试解析值类型
                parsed_value = self._parse_env_value(value)
                self._update_by_path(config, path, parsed_value)
        
        return config
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试 JSON 解析
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        # 布尔值
        lower = value.lower()
        if lower in ('true', 'yes', '1'):
            return True
        if lower in ('false', 'no', '0'):
            return False
        
        # 整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字符串
        return value
    
    def _update_by_path(self, config: Config, path: str, value: Any) -> bool:
        """通过路径更新配置"""
        parts = path.split('.')
        target = config
        
        try:
            for part in parts[:-1]:
                target = getattr(target, part)
            
            # 特殊处理 LogLevel
            if parts[-1] == 'log_level' and isinstance(value, str):
                value = LogLevel(value.lower())
            
            setattr(target, parts[-1], value)
            return True
        except (AttributeError, ValueError):
            return False
    
    def _merge_config(self, config: Config, data: dict) -> Config:
        """合并配置数据"""
        config_dict = config.to_dict()
        
        def merge_dict(target: dict, source: dict) -> dict:
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    merge_dict(target[key], value)
                else:
                    target[key] = value
            return target
        
        merged = merge_dict(config_dict, data)
        return Config.from_dict(merged)
    
    def save(self) -> Result[bool, Any]:
        """保存配置到文件"""
        try:
            data = self._config.to_dict()
            
            suffix = self._config_file.suffix.lower()
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                if suffix in ['.yaml', '.yml']:
                    try:
                        import yaml
                        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                    except ImportError:
                        # 回退到 JSON
                        json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            return ok(True)
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to save config: {e}")
    
    def get(self) -> Config:
        """获取当前配置"""
        return self._config
    
    def update(self, path: str, value: Any) -> Result[bool, Any]:
        """更新配置项（支持点号路径）
        
        Args:
            path: 配置路径，如 "system.log_level"
            value: 新值
            
        Returns:
            是否更新成功
        """
        try:
            old_value = self._get_by_path(self._config, path)
            
            if not self._update_by_path(self._config, path, value):
                return err(ErrorCode.CONFIG_ERROR, f"Invalid config path: {path}")
            
            # 通知监听器
            self._notify_change(path, old_value, value)
            
            return ok(True)
        except Exception as e:
            return err(ErrorCode.CONFIG_ERROR, f"Failed to update config: {e}")
    
    def _get_by_path(self, config: Config, path: str) -> Any:
        """通过路径获取配置值"""
        parts = path.split('.')
        target = config
        
        for part in parts:
            target = getattr(target, part)
        
        return target
    
    def register_listener(self, callback: Callable[[str, Any, Any], None]) -> None:
        """注册配置变更监听器
        
        Args:
            callback: 回调函数，参数为 (path, old_value, new_value)
        """
        self._listeners.append(callback)
    
    def unregister_listener(self, callback: Callable) -> bool:
        """取消注册监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
            return True
        return False
    
    def _notify_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """通知配置变更"""
        for listener in self._listeners:
            try:
                listener(path, old_value, new_value)
            except Exception as e:
                print(f"Config listener error: {e}")
    
    def get_value(self, path: str, default: Any = None) -> Any:
        """获取配置值（支持默认值）"""
        try:
            return self._get_by_path(self._config, path)
        except AttributeError:
            return default
    
    def reset_to_defaults(self) -> None:
        """重置为默认配置"""
        self._config = Config()
        self._notify_change("*", None, None)
