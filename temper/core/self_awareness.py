#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自感知模块 (Self-Awareness Module)

功能：
1. 系统健康自检 - 检查所有模块是否正常
2. 资源监控 - 监控CPU、内存、磁盘使用率
3. 依赖检查 - 检查外部依赖（API、文件、网络）
4. 健康报告生成 - 生成结构化的健康报告

编码规范（Codong风格）：
- 所有函数返回 {"ok": True/False, "value"/"error": ...} 格式
- 错误必须包含 error 和 message 字段
- 使用 unwrap() 提取成功值
- 使用 is_error() 检查错误

作者：AI Assistant
版本：1.0.0
"""

import os
import sys
import time
import json
import socket
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import subprocess
import threading

# 导入统一的错误处理
from ..core.result import ok, err, is_error, unwrap, ErrorCode


# =============================================================================
# 枚举类型定义
# =============================================================================

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"      # 健康
    WARNING = "warning"      # 警告
    CRITICAL = "critical"    # 严重
    UNKNOWN = "unknown"      # 未知


class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


class DependencyType(Enum):
    """依赖类型枚举"""
    API = "api"
    FILE = "file"
    NETWORK = "network"
    SERVICE = "service"


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class HealthCheckResult:
    """健康检查结果数据类"""
    name: str
    status: HealthStatus
    message: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details
        }


@dataclass
class ResourceUsage:
    """资源使用数据类"""
    resource_type: ResourceType
    usage_percent: float
    total: float
    used: float
    available: float
    unit: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "usage_percent": round(self.usage_percent, 2),
            "total": round(self.total, 2),
            "used": round(self.used, 2),
            "available": round(self.available, 2),
            "unit": self.unit,
            "timestamp": self.timestamp
        }


@dataclass
class DependencyStatus:
    """依赖状态数据类"""
    name: str
    dep_type: DependencyType
    is_available: bool
    response_time_ms: float
    last_checked: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.dep_type.value,
            "is_available": self.is_available,
            "response_time_ms": round(self.response_time_ms, 2),
            "last_checked": self.last_checked,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class HealthReport:
    """健康报告数据类"""
    timestamp: float
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    resources: List[ResourceUsage]
    dependencies: List[DependencyStatus]
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "overall_status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "resources": [r.to_dict() for r in self.resources],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "summary": self.summary
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# 资源监控类
# =============================================================================

class ResourceMonitor:
    """
    资源监控类
    
    功能：
    - 监控CPU使用率
    - 监控内存使用率
    - 监控磁盘使用率
    - 监控网络状态
    
    仅使用Python标准库实现
    """
    
    def __init__(self):
        """初始化资源监控器"""
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 1.0  # 缓存1秒
        
    def _read_file(self, path: str) -> Dict[str, Any]:
        """
        读取文件内容
        
        Args:
            path: 文件路径
            
        Returns:
            文件内容或错误
        """
        try:
            with open(path, 'r') as f:
                return ok(f.read())
        except FileNotFoundError:
            return err("FILE_NOT_FOUND", f"文件不存在: {path}")
        except PermissionError:
            return err("PERMISSION_DENIED", f"无权限读取文件: {path}")
        except Exception as e:
            return err("READ_ERROR", f"读取文件失败: {str(e)}")
    
    def _parse_meminfo(self, content: str) -> Dict[str, int]:
        """
        解析 /proc/meminfo 内容
        
        Args:
            content: meminfo文件内容
            
        Returns:
            内存信息字典（单位为KB）
        """
        meminfo = {}
        for line in content.strip().split('\n'):
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                # 提取数值（移除单位）
                value_str = parts[1].strip().split()[0]
                try:
                    meminfo[key] = int(value_str)
                except ValueError:
                    pass
        return meminfo
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """
        获取CPU使用率
        
        通过读取 /proc/stat 计算CPU使用率
        
        Returns:
            ResourceUsage 对象或错误
        """
        try:
            # 读取第一次采样
            result1 = self._read_file('/proc/stat')
            if is_error(result1):
                return result1
            
            stat1 = unwrap(result1)
            cpu_line1 = stat1.split('\n')[0]
            values1 = list(map(int, cpu_line1.split()[1:]))
            
            # 等待一段时间
            time.sleep(0.1)
            
            # 读取第二次采样
            result2 = self._read_file('/proc/stat')
            if is_error(result2):
                return result2
            
            stat2 = unwrap(result2)
            cpu_line2 = stat2.split('\n')[0]
            values2 = list(map(int, cpu_line2.split()[1:]))
            
            # 计算CPU使用率
            # user, nice, system, idle, iowait, irq, softirq, steal
            total1 = sum(values1)
            total2 = sum(values2)
            idle1 = values1[3] + values1[4]  # idle + iowait
            idle2 = values2[3] + values2[4]
            
            total_diff = total2 - total1
            idle_diff = idle2 - idle1
            
            if total_diff == 0:
                usage_percent = 0.0
            else:
                usage_percent = 100.0 * (1.0 - idle_diff / total_diff)
            
            # 获取CPU核心数
            cpu_count = os.cpu_count() or 1
            
            resource_usage = ResourceUsage(
                resource_type=ResourceType.CPU,
                usage_percent=max(0.0, min(100.0, usage_percent)),
                total=cpu_count,
                used=cpu_count * usage_percent / 100.0,
                available=cpu_count * (100.0 - usage_percent) / 100.0,
                unit="cores",
                timestamp=time.time()
            )
            
            return ok(resource_usage)
            
        except Exception as e:
            return err("CPU_MONITOR_ERROR", f"获取CPU使用率失败: {str(e)}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        获取内存使用率
        
        通过读取 /proc/meminfo 计算内存使用率
        
        Returns:
            ResourceUsage 对象或错误
        """
        try:
            result = self._read_file('/proc/meminfo')
            if is_error(result):
                return result
            
            content = unwrap(result)
            meminfo = self._parse_meminfo(content)
            
            # 计算内存使用
            total = meminfo.get('MemTotal', 0)
            free = meminfo.get('MemFree', 0)
            buffers = meminfo.get('Buffers', 0)
            cached = meminfo.get('Cached', 0)
            
            # 可用内存 = free + buffers + cached
            available = free + buffers + cached
            used = total - available
            
            if total == 0:
                usage_percent = 0.0
            else:
                usage_percent = 100.0 * used / total
            
            resource_usage = ResourceUsage(
                resource_type=ResourceType.MEMORY,
                usage_percent=round(usage_percent, 2),
                total=total / 1024,  # 转换为MB
                used=used / 1024,
                available=available / 1024,
                unit="MB",
                timestamp=time.time()
            )
            
            return ok(resource_usage)
            
        except Exception as e:
            return err("MEMORY_MONITOR_ERROR", f"获取内存使用率失败: {str(e)}")
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """
        获取磁盘使用率
        
        使用 os.statvfs 获取磁盘使用情况
        
        Args:
            path: 要检查的磁盘路径
            
        Returns:
            ResourceUsage 对象或错误
        """
        try:
            stat = os.statvfs(path)
            
            # 计算磁盘使用情况
            total_blocks = stat.f_blocks
            free_blocks = stat.f_bfree
            available_blocks = stat.f_bavail
            block_size = stat.f_frsize
            
            total = total_blocks * block_size
            available = available_blocks * block_size
            used = total - available
            
            if total == 0:
                usage_percent = 0.0
            else:
                usage_percent = 100.0 * used / total
            
            # 转换为GB
            gb_factor = 1024 * 1024 * 1024
            
            resource_usage = ResourceUsage(
                resource_type=ResourceType.DISK,
                usage_percent=round(usage_percent, 2),
                total=round(total / gb_factor, 2),
                used=round(used / gb_factor, 2),
                available=round(available / gb_factor, 2),
                unit="GB",
                timestamp=time.time()
            )
            
            return ok(resource_usage)
            
        except FileNotFoundError:
            return err("PATH_NOT_FOUND", f"路径不存在: {path}")
        except Exception as e:
            return err("DISK_MONITOR_ERROR", f"获取磁盘使用率失败: {str(e)}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """
        获取网络状态
        
        通过检查网络接口状态来判断网络是否可用
        
        Returns:
            ResourceUsage 对象或错误
        """
        try:
            # 读取网络接口统计
            result = self._read_file('/proc/net/dev')
            if is_error(result):
                # 如果无法读取，使用简单检查
                return self._simple_network_check()
            
            content = unwrap(result)
            lines = content.strip().split('\n')[2:]  # 跳过标题行
            
            total_rx = 0
            total_tx = 0
            active_interfaces = 0
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 9:
                    iface = parts[0].rstrip(':')
                    if iface != 'lo':  # 排除回环接口
                        rx_bytes = int(parts[1])
                        tx_bytes = int(parts[9])
                        if rx_bytes > 0 or tx_bytes > 0:
                            active_interfaces += 1
                        total_rx += rx_bytes
                        total_tx += tx_bytes
            
            # 计算网络健康度（基于活跃接口数）
            if active_interfaces > 0:
                health_percent = 100.0
            else:
                health_percent = 0.0
            
            # 转换为MB
            mb_factor = 1024 * 1024
            
            resource_usage = ResourceUsage(
                resource_type=ResourceType.NETWORK,
                usage_percent=health_percent,
                total=round((total_rx + total_tx) / mb_factor, 2),
                used=round(total_tx / mb_factor, 2),
                available=round(total_rx / mb_factor, 2),
                unit="MB",
                timestamp=time.time()
            )
            
            return ok(resource_usage)
            
        except Exception as e:
            return err("NETWORK_MONITOR_ERROR", f"获取网络状态失败: {str(e)}")
    
    def _simple_network_check(self) -> Dict[str, Any]:
        """
        简单的网络检查（备用方案）
        
        Returns:
            ResourceUsage 对象或错误
        """
        try:
            # 尝试解析一个公共DNS来检查网络
            socket.getaddrinfo('8.8.8.8', None)
            
            resource_usage = ResourceUsage(
                resource_type=ResourceType.NETWORK,
                usage_percent=100.0,
                total=0,
                used=0,
                available=0,
                unit="MB",
                timestamp=time.time()
            )
            return ok(resource_usage)
        except Exception:
            resource_usage = ResourceUsage(
                resource_type=ResourceType.NETWORK,
                usage_percent=0.0,
                total=0,
                used=0,
                available=0,
                unit="MB",
                timestamp=time.time()
            )
            return ok(resource_usage)
    
    def get_all_resources(self) -> Dict[str, Any]:
        """
        获取所有资源使用情况
        
        Returns:
            资源列表或错误
        """
        resources = []
        
        # CPU
        cpu_result = self.get_cpu_usage()
        if not is_error(cpu_result):
            resources.append(unwrap(cpu_result))
        
        # 内存
        mem_result = self.get_memory_usage()
        if not is_error(mem_result):
            resources.append(unwrap(mem_result))
        
        # 磁盘
        disk_result = self.get_disk_usage()
        if not is_error(disk_result):
            resources.append(unwrap(disk_result))
        
        # 网络
        net_result = self.get_network_status()
        if not is_error(net_result):
            resources.append(unwrap(net_result))
        
        return ok(resources)


# =============================================================================
# 依赖检查类
# =============================================================================

class DependencyChecker:
    """
    依赖检查类
    
    功能：
    - 检查API可用性
    - 检查文件存在性和可读性
    - 检查网络连接
    - 检查服务状态
    
    仅使用Python标准库实现
    """
    
    def __init__(self, timeout: float = 5.0):
        """
        初始化依赖检查器
        
        Args:
            timeout: 检查超时时间（秒）
        """
        self.timeout = timeout
        self._dependencies: Dict[str, Dict[str, Any]] = {}
    
    def register_dependency(self, name: str, dep_type: DependencyType, 
                           check_func: Callable[[], Dict[str, Any]],
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        注册一个依赖项
        
        Args:
            name: 依赖项名称
            dep_type: 依赖类型
            check_func: 检查函数，返回 DependencyStatus 或错误
            metadata: 元数据
            
        Returns:
            成功或错误
        """
        try:
            self._dependencies[name] = {
                "type": dep_type,
                "check_func": check_func,
                "metadata": metadata or {}
            }
            return ok(True)
        except Exception as e:
            return err("REGISTER_ERROR", f"注册依赖项失败: {str(e)}")
    
    def check_api(self, url: str, method: str = "GET", 
                  headers: Optional[Dict[str, str]] = None,
                  expected_status: int = 200) -> Dict[str, Any]:
        """
        检查API可用性
        
        Args:
            url: API URL
            method: HTTP方法
            headers: 请求头
            expected_status: 期望的HTTP状态码
            
        Returns:
            DependencyStatus 对象或错误
        """
        start_time = time.time()
        
        try:
            req = urllib.request.Request(
                url, 
                method=method,
                headers=headers or {},
                timeout=self.timeout
            )
            
            with urllib.request.urlopen(req) as response:
                response_time = (time.time() - start_time) * 1000
                is_available = response.status == expected_status
                
                status = DependencyStatus(
                    name=url,
                    dep_type=DependencyType.API,
                    is_available=is_available,
                    response_time_ms=response_time,
                    last_checked=time.time(),
                    error_message=None if is_available else f"状态码: {response.status}",
                    metadata={
                        "status_code": response.status,
                        "expected_status": expected_status
                    }
                )
                return ok(status)
                
        except urllib.error.HTTPError as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=url,
                dep_type=DependencyType.API,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"HTTP错误: {e.code}",
                metadata={"status_code": e.code}
            )
            return ok(status)
            
        except urllib.error.URLError as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=url,
                dep_type=DependencyType.API,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"URL错误: {str(e.reason)}",
                metadata={}
            )
            return ok(status)
            
        except socket.timeout:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=url,
                dep_type=DependencyType.API,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message="请求超时",
                metadata={}
            )
            return ok(status)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=url,
                dep_type=DependencyType.API,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"检查失败: {str(e)}",
                metadata={}
            )
            return ok(status)
    
    def check_file(self, file_path: str, readable: bool = True, 
                   writable: bool = False) -> Dict[str, Any]:
        """
        检查文件依赖
        
        Args:
            file_path: 文件路径
            readable: 是否要求可读
            writable: 是否要求可写
            
        Returns:
            DependencyStatus 对象或错误
        """
        start_time = time.time()
        
        try:
            exists = os.path.exists(file_path)
            is_file = os.path.isfile(file_path) if exists else False
            
            can_read = os.access(file_path, os.R_OK) if exists else False
            can_write = os.access(file_path, os.W_OK) if exists else False
            
            checks_passed = True
            error_messages = []
            
            if not exists:
                checks_passed = False
                error_messages.append("文件不存在")
            elif not is_file:
                checks_passed = False
                error_messages.append("路径不是文件")
            else:
                if readable and not can_read:
                    checks_passed = False
                    error_messages.append("文件不可读")
                if writable and not can_write:
                    checks_passed = False
                    error_messages.append("文件不可写")
            
            response_time = (time.time() - start_time) * 1000
            
            status = DependencyStatus(
                name=file_path,
                dep_type=DependencyType.FILE,
                is_available=checks_passed,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message="; ".join(error_messages) if error_messages else None,
                metadata={
                    "exists": exists,
                    "is_file": is_file,
                    "readable": can_read,
                    "writable": can_write
                }
            )
            return ok(status)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=file_path,
                dep_type=DependencyType.FILE,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"检查失败: {str(e)}",
                metadata={}
            )
            return ok(status)
    
    def check_network(self, host: str, port: int = 80) -> Dict[str, Any]:
        """
        检查网络连接
        
        Args:
            host: 主机地址
            port: 端口号
            
        Returns:
            DependencyStatus 对象或错误
        """
        start_time = time.time()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            response_time = (time.time() - start_time) * 1000
            is_available = result == 0
            
            status = DependencyStatus(
                name=f"{host}:{port}",
                dep_type=DependencyType.NETWORK,
                is_available=is_available,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=None if is_available else f"连接失败 (错误码: {result})",
                metadata={
                    "host": host,
                    "port": port,
                    "error_code": result
                }
            )
            return ok(status)
            
        except socket.gaierror:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=f"{host}:{port}",
                dep_type=DependencyType.NETWORK,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message="无法解析主机名",
                metadata={"host": host, "port": port}
            )
            return ok(status)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=f"{host}:{port}",
                dep_type=DependencyType.NETWORK,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"检查失败: {str(e)}",
                metadata={"host": host, "port": port}
            )
            return ok(status)
    
    def check_service(self, service_name: str, 
                      pid_file: Optional[str] = None,
                      port: Optional[int] = None) -> Dict[str, Any]:
        """
        检查服务状态
        
        Args:
            service_name: 服务名称
            pid_file: PID文件路径（可选）
            port: 服务端口（可选）
            
        Returns:
            DependencyStatus 对象或错误
        """
        start_time = time.time()
        
        try:
            is_running = False
            metadata = {"service_name": service_name}
            
            # 方法1: 通过PID文件检查
            if pid_file:
                pid_result = self._check_pid_file(pid_file)
                if not is_error(pid_result):
                    pid_info = unwrap(pid_result)
                    is_running = pid_info.get("is_running", False)
                    metadata["pid_file"] = pid_file
                    metadata["pid"] = pid_info.get("pid")
            
            # 方法2: 通过端口检查
            if port and not is_running:
                port_result = self.check_network("127.0.0.1", port)
                if not is_error(port_result):
                    port_status = unwrap(port_result)
                    is_running = port_status.is_available
                    metadata["port"] = port
            
            # 方法3: 通过进程名检查（简单实现）
            if not is_running:
                proc_result = self._check_process(service_name)
                if not is_error(proc_result):
                    is_running = unwrap(proc_result)
                    metadata["process_check"] = True
            
            response_time = (time.time() - start_time) * 1000
            
            status = DependencyStatus(
                name=service_name,
                dep_type=DependencyType.SERVICE,
                is_available=is_running,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=None if is_running else "服务未运行",
                metadata=metadata
            )
            return ok(status)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = DependencyStatus(
                name=service_name,
                dep_type=DependencyType.SERVICE,
                is_available=False,
                response_time_ms=response_time,
                last_checked=time.time(),
                error_message=f"检查失败: {str(e)}",
                metadata={"service_name": service_name}
            )
            return ok(status)
    
    def _check_pid_file(self, pid_file: str) -> Dict[str, Any]:
        """
        检查PID文件
        
        Args:
            pid_file: PID文件路径
            
        Returns:
            PID信息或错误
        """
        try:
            if not os.path.exists(pid_file):
                return ok({"is_running": False, "pid": None})
            
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            try:
                os.kill(pid, 0)
                return ok({"is_running": True, "pid": pid})
            except ProcessLookupError:
                return ok({"is_running": False, "pid": pid})
            
        except Exception as e:
            return err("PID_CHECK_ERROR", f"检查PID文件失败: {str(e)}")
    
    def _check_process(self, process_name: str) -> Dict[str, Any]:
        """
        检查进程是否存在
        
        Args:
            process_name: 进程名称
            
        Returns:
            是否存在或错误
        """
        try:
            # 读取 /proc 目录
            for pid in os.listdir('/proc'):
                if pid.isdigit():
                    try:
                        with open(f'/proc/{pid}/comm', 'r') as f:
                            comm = f.read().strip()
                            if process_name.lower() in comm.lower():
                                return ok(True)
                    except:
                        continue
            return ok(False)
        except Exception as e:
            return err("PROCESS_CHECK_ERROR", f"检查进程失败: {str(e)}")
    
    def check_all_registered(self) -> Dict[str, Any]:
        """
        检查所有已注册的依赖项
        
        Returns:
            依赖状态列表或错误
        """
        results = []
        
        for name, config in self._dependencies.items():
            try:
                check_func = config["check_func"]
                result = check_func()
                if not is_error(result):
                    results.append(unwrap(result))
            except Exception as e:
                results.append(DependencyStatus(
                    name=name,
                    dep_type=config.get("type", DependencyType.SERVICE),
                    is_available=False,
                    response_time_ms=0,
                    last_checked=time.time(),
                    error_message=f"检查函数执行失败: {str(e)}",
                    metadata=config.get("metadata", {})
                ))
        
        return ok(results)


# =============================================================================
# 健康检查类
# =============================================================================

class HealthChecker:
    """
    健康检查类
    
    功能：
    - 注册健康检查项
    - 执行健康检查
    - 评估整体健康状态
    - 生成健康检查结果
    
    仅使用Python标准库实现
    """
    
    def __init__(self):
        """初始化健康检查器"""
        self._checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._resource_monitor = ResourceMonitor()
        self._dependency_checker = DependencyChecker()
        self._thresholds = {
            "cpu_warning": 70.0,
            "cpu_critical": 90.0,
            "memory_warning": 80.0,
            "memory_critical": 95.0,
            "disk_warning": 80.0,
            "disk_critical": 95.0,
        }
    
    def set_thresholds(self, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """
        设置阈值
        
        Args:
            thresholds: 阈值字典
            
        Returns:
            成功或错误
        """
        try:
            self._thresholds.update(thresholds)
            return ok(True)
        except Exception as e:
            return err("SET_THRESHOLD_ERROR", f"设置阈值失败: {str(e)}")
    
    def register_check(self, name: str, 
                      check_func: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        """
        注册健康检查项
        
        Args:
            name: 检查项名称
            check_func: 检查函数，返回 HealthCheckResult 或错误
            
        Returns:
            成功或错误
        """
        try:
            self._checks[name] = check_func
            return ok(True)
        except Exception as e:
            return err("REGISTER_ERROR", f"注册检查项失败: {str(e)}")
    
    def unregister_check(self, name: str) -> Dict[str, Any]:
        """
        注销健康检查项
        
        Args:
            name: 检查项名称
            
        Returns:
            成功或错误
        """
        try:
            if name in self._checks:
                del self._checks[name]
                return ok(True)
            return err("NOT_FOUND", f"检查项不存在: {name}")
        except Exception as e:
            return err("UNREGISTER_ERROR", f"注销检查项失败: {str(e)}")
    
    def check_resource_health(self) -> Dict[str, Any]:
        """
        检查资源健康状态
        
        Returns:
            HealthCheckResult 列表或错误
        """
        results = []
        
        # 检查CPU
        cpu_result = self._resource_monitor.get_cpu_usage()
        if not is_error(cpu_result):
            cpu_usage = unwrap(cpu_result)
            status = self._evaluate_resource_status(
                cpu_usage.usage_percent,
                self._thresholds["cpu_warning"],
                self._thresholds["cpu_critical"]
            )
            results.append(HealthCheckResult(
                name="cpu_usage",
                status=status,
                message=f"CPU使用率: {cpu_usage.usage_percent:.1f}%",
                timestamp=time.time(),
                details=cpu_usage.to_dict()
            ))
        
        # 检查内存
        mem_result = self._resource_monitor.get_memory_usage()
        if not is_error(mem_result):
            mem_usage = unwrap(mem_result)
            status = self._evaluate_resource_status(
                mem_usage.usage_percent,
                self._thresholds["memory_warning"],
                self._thresholds["memory_critical"]
            )
            results.append(HealthCheckResult(
                name="memory_usage",
                status=status,
                message=f"内存使用率: {mem_usage.usage_percent:.1f}%",
                timestamp=time.time(),
                details=mem_usage.to_dict()
            ))
        
        # 检查磁盘
        disk_result = self._resource_monitor.get_disk_usage()
        if not is_error(disk_result):
            disk_usage = unwrap(disk_result)
            status = self._evaluate_resource_status(
                disk_usage.usage_percent,
                self._thresholds["disk_warning"],
                self._thresholds["disk_critical"]
            )
            results.append(HealthCheckResult(
                name="disk_usage",
                status=status,
                message=f"磁盘使用率: {disk_usage.usage_percent:.1f}%",
                timestamp=time.time(),
                details=disk_usage.to_dict()
            ))
        
        # 检查网络
        net_result = self._resource_monitor.get_network_status()
        if not is_error(net_result):
            net_usage = unwrap(net_result)
            status = HealthStatus.HEALTHY if net_usage.usage_percent > 0 else HealthStatus.WARNING
            results.append(HealthCheckResult(
                name="network_status",
                status=status,
                message="网络正常" if status == HealthStatus.HEALTHY else "网络可能不可用",
                timestamp=time.time(),
                details=net_usage.to_dict()
            ))
        
        return ok(results)
    
    def _evaluate_resource_status(self, usage: float, warning: float, 
                                   critical: float) -> HealthStatus:
        """
        评估资源状态
        
        Args:
            usage: 使用率
            warning: 警告阈值
            critical: 严重阈值
            
        Returns:
            健康状态
        """
        if usage >= critical:
            return HealthStatus.CRITICAL
        elif usage >= warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def check_dependencies(self, dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检查依赖项
        
        Args:
            dependencies: 依赖配置列表
                每个依赖包含：name, type, config
                
        Returns:
            HealthCheckResult 列表或错误
        """
        results = []
        
        for dep in dependencies:
            name = dep.get("name", "unknown")
            dep_type = dep.get("type", "api")
            config = dep.get("config", {})
            
            try:
                if dep_type == "api":
                    result = self._dependency_checker.check_api(
                        config.get("url"),
                        config.get("method", "GET"),
                        config.get("headers"),
                        config.get("expected_status", 200)
                    )
                elif dep_type == "file":
                    result = self._dependency_checker.check_file(
                        config.get("path"),
                        config.get("readable", True),
                        config.get("writable", False)
                    )
                elif dep_type == "network":
                    result = self._dependency_checker.check_network(
                        config.get("host"),
                        config.get("port", 80)
                    )
                elif dep_type == "service":
                    result = self._dependency_checker.check_service(
                        name,
                        config.get("pid_file"),
                        config.get("port")
                    )
                else:
                    results.append(HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNKNOWN,
                        message=f"未知的依赖类型: {dep_type}",
                        timestamp=time.time()
                    ))
                    continue
                
                if not is_error(result):
                    dep_status = unwrap(result)
                    status = HealthStatus.HEALTHY if dep_status.is_available else HealthStatus.CRITICAL
                    results.append(HealthCheckResult(
                        name=name,
                        status=status,
                        message=f"{'可用' if dep_status.is_available else '不可用'} ({dep_status.response_time_ms:.0f}ms)",
                        timestamp=time.time(),
                        details=dep_status.to_dict()
                    ))
                    
            except Exception as e:
                results.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"检查失败: {str(e)}",
                    timestamp=time.time()
                ))
        
        return ok(results)
    
    def run_custom_checks(self) -> Dict[str, Any]:
        """
        运行所有自定义检查
        
        Returns:
            HealthCheckResult 列表或错误
        """
        results = []
        
        for name, check_func in self._checks.items():
            try:
                result = check_func()
                if not is_error(result):
                    results.append(unwrap(result))
                else:
                    results.append(HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNKNOWN,
                        message=f"检查失败: {result.get('message', '未知错误')}",
                        timestamp=time.time()
                    ))
            except Exception as e:
                results.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"检查异常: {str(e)}",
                    timestamp=time.time()
                ))
        
        return ok(results)
    
    def run_all_checks(self, dependencies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        运行所有健康检查
        
        Args:
            dependencies: 依赖配置列表（可选）
            
        Returns:
            HealthCheckResult 列表或错误
        """
        all_results = []
        
        # 资源检查
        resource_result = self.check_resource_health()
        if not is_error(resource_result):
            all_results.extend(unwrap(resource_result))
        
        # 依赖检查
        if dependencies:
            dep_result = self.check_dependencies(dependencies)
            if not is_error(dep_result):
                all_results.extend(unwrap(dep_result))
        
        # 自定义检查
        custom_result = self.run_custom_checks()
        if not is_error(custom_result):
            all_results.extend(unwrap(custom_result))
        
        return ok(all_results)
    
    def evaluate_overall_status(self, checks: List[HealthCheckResult]) -> HealthStatus:
        """
        评估整体健康状态
        
        Args:
            checks: 检查结果列表
            
        Returns:
            整体健康状态
        """
        if not checks:
            return HealthStatus.UNKNOWN
        
        has_critical = any(c.status == HealthStatus.CRITICAL for c in checks)
        has_warning = any(c.status == HealthStatus.WARNING for c in checks)
        
        if has_critical:
            return HealthStatus.CRITICAL
        elif has_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


# =============================================================================
# 全局健康检查函数
# =============================================================================

def create_health_report(health_checker: Optional[HealthChecker] = None,
                        dependencies: Optional[List[Dict[str, Any]]] = None,
                        include_resources: bool = True) -> Dict[str, Any]:
    """
    创建健康报告
    
    全局函数，用于生成完整的系统健康报告
    
    Args:
        health_checker: 健康检查器实例（可选，默认创建新实例）
        dependencies: 依赖配置列表（可选）
        include_resources: 是否包含资源信息
        
    Returns:
        HealthReport 对象或错误
    """
    try:
        if health_checker is None:
            health_checker = HealthChecker()
        
        # 运行所有检查
        checks_result = health_checker.run_all_checks(dependencies)
        if is_error(checks_result):
            return checks_result
        
        checks = unwrap(checks_result)
        
        # 获取资源信息
        resources = []
        if include_resources:
            resource_monitor = ResourceMonitor()
            resource_result = resource_monitor.get_all_resources()
            if not is_error(resource_result):
                resources = unwrap(resource_result)
        
        # 获取依赖信息
        dep_statuses = []
        if dependencies:
            dep_checker = DependencyChecker()
            for dep in dependencies:
                name = dep.get("name", "unknown")
                dep_type = dep.get("type", "api")
                config = dep.get("config", {})
                
                try:
                    if dep_type == "api":
                        result = dep_checker.check_api(
                            config.get("url"),
                            config.get("method", "GET"),
                            config.get("headers"),
                            config.get("expected_status", 200)
                        )
                    elif dep_type == "file":
                        result = dep_checker.check_file(
                            config.get("path"),
                            config.get("readable", True),
                            config.get("writable", False)
                        )
                    elif dep_type == "network":
                        result = dep_checker.check_network(
                            config.get("host"),
                            config.get("port", 80)
                        )
                    elif dep_type == "service":
                        result = dep_checker.check_service(
                            name,
                            config.get("pid_file"),
                            config.get("port")
                        )
                    else:
                        continue
                    
                    if not is_error(result):
                        dep_statuses.append(unwrap(result))
                except:
                    pass
        
        # 评估整体状态
        overall_status = health_checker.evaluate_overall_status(checks)
        
        # 生成摘要
        summary = {
            "total_checks": len(checks),
            "healthy_count": sum(1 for c in checks if c.status == HealthStatus.HEALTHY),
            "warning_count": sum(1 for c in checks if c.status == HealthStatus.WARNING),
            "critical_count": sum(1 for c in checks if c.status == HealthStatus.CRITICAL),
            "unknown_count": sum(1 for c in checks if c.status == HealthStatus.UNKNOWN),
        }
        
        # 创建报告
        report = HealthReport(
            timestamp=time.time(),
            overall_status=overall_status,
            checks=checks,
            resources=resources,
            dependencies=dep_statuses,
            summary=summary
        )
        
        return ok(report)
        
    except Exception as e:
        return err("REPORT_GENERATION_ERROR", f"生成健康报告失败: {str(e)}")


def quick_health_check() -> Dict[str, Any]:
    """
    快速健康检查
    
    全局函数，执行简单的系统健康检查
    
    Returns:
        检查结果字典或错误
    """
    try:
        health_checker = HealthChecker()
        
        # 只检查资源
        result = health_checker.check_resource_health()
        if is_error(result):
            return result
        
        checks = unwrap(result)
        overall_status = health_checker.evaluate_overall_status(checks)
        
        return ok({
            "status": overall_status.value,
            "checks": [c.to_dict() for c in checks],
            "timestamp": time.time()
        })
        
    except Exception as e:
        return err("QUICK_CHECK_ERROR", f"快速健康检查失败: {str(e)}")


def check_system_readiness(required_deps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    检查系统就绪状态
    
    全局函数，检查系统是否准备好运行
    
    Args:
        required_deps: 必需的依赖列表
        
    Returns:
        就绪状态或错误
    """
    try:
        health_checker = HealthChecker()
        dep_checker = DependencyChecker()
        
        # 检查资源
        resource_result = health_checker.check_resource_health()
        if is_error(resource_result):
            return resource_result
        
        resource_checks = unwrap(resource_result)
        
        # 检查必需依赖
        failed_deps = []
        for dep in required_deps:
            name = dep.get("name", "unknown")
            dep_type = dep.get("type", "api")
            config = dep.get("config", {})
            
            is_available = False
            
            try:
                if dep_type == "api":
                    result = dep_checker.check_api(
                        config.get("url"),
                        config.get("method", "GET"),
                        config.get("headers"),
                        config.get("expected_status", 200)
                    )
                elif dep_type == "file":
                    result = dep_checker.check_file(
                        config.get("path"),
                        config.get("readable", True),
                        config.get("writable", False)
                    )
                elif dep_type == "network":
                    result = dep_checker.check_network(
                        config.get("host"),
                        config.get("port", 80)
                    )
                elif dep_type == "service":
                    result = dep_checker.check_service(
                        name,
                        config.get("pid_file"),
                        config.get("port")
                    )
                else:
                    continue
                
                if not is_error(result):
                    dep_status = unwrap(result)
                    is_available = dep_status.is_available
            except:
                pass
            
            if not is_available:
                failed_deps.append(name)
        
        # 评估就绪状态
        critical_resources = [c for c in resource_checks if c.status == HealthStatus.CRITICAL]
        
        is_ready = len(critical_resources) == 0 and len(failed_deps) == 0
        
        return ok({
            "is_ready": is_ready,
            "resource_status": health_checker.evaluate_overall_status(resource_checks).value,
            "failed_dependencies": failed_deps,
            "critical_resources": [c.name for c in critical_resources],
            "timestamp": time.time()
        })
        
    except Exception as e:
        return err("READINESS_CHECK_ERROR", f"系统就绪检查失败: {str(e)}")


# =============================================================================
# 主程序入口（测试）
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("自感知模块测试")
    print("=" * 60)
    
    # 测试资源监控
    print("\n[1] 测试资源监控")
    print("-" * 40)
    
    monitor = ResourceMonitor()
    
    # CPU
    cpu_result = monitor.get_cpu_usage()
    if not is_error(cpu_result):
        cpu = unwrap(cpu_result)
        print(f"CPU使用率: {cpu.usage_percent:.1f}%")
    else:
        print(f"CPU检查失败: {cpu_result.get('message')}")
    
    # 内存
    mem_result = monitor.get_memory_usage()
    if not is_error(mem_result):
        mem = unwrap(mem_result)
        print(f"内存使用率: {mem.usage_percent:.1f}% ({mem.used:.0f}/{mem.total:.0f} MB)")
    else:
        print(f"内存检查失败: {mem_result.get('message')}")
    
    # 磁盘
    disk_result = monitor.get_disk_usage()
    if not is_error(disk_result):
        disk = unwrap(disk_result)
        print(f"磁盘使用率: {disk.usage_percent:.1f}% ({disk.used:.1f}/{disk.total:.1f} GB)")
    else:
        print(f"磁盘检查失败: {disk_result.get('message')}")
    
    # 网络
    net_result = monitor.get_network_status()
    if not is_error(net_result):
        net = unwrap(net_result)
        print(f"网络状态: {'正常' if net.usage_percent > 0 else '异常'}")
    else:
        print(f"网络检查失败: {net_result.get('message')}")
    
    # 测试依赖检查
    print("\n[2] 测试依赖检查")
    print("-" * 40)
    
    dep_checker = DependencyChecker()
    
    # 检查文件
    file_result = dep_checker.check_file("/etc/passwd", readable=True)
    if not is_error(file_result):
        file_status = unwrap(file_result)
        print(f"文件检查 (/etc/passwd): {'✓' if file_status.is_available else '✗'}")
    
    # 检查网络
    net_check_result = dep_checker.check_network("8.8.8.8", 53)
    if not is_error(net_check_result):
        net_status = unwrap(net_check_result)
        print(f"网络检查 (8.8.8.8:53): {'✓' if net_status.is_available else '✗'} ({net_status.response_time_ms:.1f}ms)")
    
    # 测试健康检查
    print("\n[3] 测试健康检查")
    print("-" * 40)
    
    health_checker = HealthChecker()
    
    # 注册自定义检查
    def custom_check():
        return ok(HealthCheckResult(
            name="custom_check",
            status=HealthStatus.HEALTHY,
            message="自定义检查通过",
            timestamp=time.time()
        ))
    
    health_checker.register_check("custom", custom_check)
    
    # 运行检查
    check_result = health_checker.run_all_checks()
    if not is_error(check_result):
        checks = unwrap(check_result)
        for check in checks:
            status_icon = "✓" if check.status == HealthStatus.HEALTHY else "⚠" if check.status == HealthStatus.WARNING else "✗"
            print(f"{status_icon} {check.name}: {check.message}")
    
    # 测试快速健康检查
    print("\n[4] 测试快速健康检查")
    print("-" * 40)
    
    quick_result = quick_health_check()
    if not is_error(quick_result):
        quick = unwrap(quick_result)
        print(f"整体状态: {quick['status']}")
    
    # 测试健康报告
    print("\n[5] 测试健康报告生成")
    print("-" * 40)
    
    report_result = create_health_report()
    if not is_error(report_result):
        report = unwrap(report_result)
        print(f"报告状态: {report.overall_status.value}")
        print(f"检查项数: {report.summary.get('total_checks', 0)}")
        print(f"健康: {report.summary.get('healthy_count', 0)}")
        print(f"警告: {report.summary.get('warning_count', 0)}")
        print(f"严重: {report.summary.get('critical_count', 0)}")
        
        # 输出JSON报告
        print("\nJSON报告预览:")
        print(report.to_json()[:500] + "...")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
