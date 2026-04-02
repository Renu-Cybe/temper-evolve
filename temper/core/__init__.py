#!/usr/bin/env python3
"""
🧊 Temper Core - 四自系统核心模块

四自系统：
- 自感知（Self-Awareness）：健康自检、状态监控
- 自适应（Self-Adaptive）：动态调参、性能优化
- 自组织（Self-Organizing）：工作流合成、任务编排
- 自编译（Self-Compiling）：自我修复、代码生成

铁三角原则：
- 信任原则：透明可审计，不擅自修改用户文件
- 复利原则：能力持久化，下次启动继承
- 杠杆原则：配置驱动，拒绝硬编码
"""

# 版本信息
__version__ = "3.0.0"
__author__ = "Temper AI"

# 导出核心错误处理
from .errors import (
    ok, err, is_error, is_ok, unwrap, unwrap_or_raise,
    map_result, bind_result, CodongError, ErrorCode,
    file_not_found, file_read_error, file_write_error,
    permission_denied, network_error, timeout_error,
    validation_error, not_found
)

# 导出配置系统
from .config import (
    Config, ConfigValidator, get_config,
    config_get, config_set, config_save, config_reload
)

# 导出审计系统
from .audit import (
    AuditLogger, BackupManager, RollbackManager,
    init_audit_system, get_audit_logger, get_backup_manager, get_rollback_manager,
    audited_operation, audited_context, safe_file_write, safe_file_delete
)

# 导出持久化系统
from .persistence import (
    StateManager, Snapshot, Migration,
    get_state_manager, persist_get, persist_set,
    persist_save, persist_load, persist_restore,
    create_full_backup, restore_from_backup
)

# 导出自感知模块
from .self_awareness import (
    ResourceMonitor, DependencyChecker, HealthChecker,
    HealthStatus, HealthReport, quick_health_check,
    create_health_report, check_system_readiness
)

# 导出自适应模块
from .self_adaptive import (
    ParameterTuner, PerformanceOptimizer, RateLimiter,
    ConfigHotUpdater, AdaptiveManager, PerformanceMetrics,
    create_adaptive_manager, get_global_manager
)

# 导出自组织模块
from .self_organizing import (
    Workflow, Task, TaskExecutor, DependencyResolver, WorkflowEngine,
    create_workflow, run_workflow, serial_tasks, parallel_tasks,
    conditional_workflow, compose_workflows
)

# 导出自编译模块
from .self_compiling import (
    CodeTemplate, CodeGenerator, SelfRepair, HotLoader,
    SelfCompilingModule, compile_template,
    self_compile, enable_hot_reload
)


# 四自系统整合器
class FourSelfSystem:
    """
    四自系统整合器
    
    整合自感知、自适应、自组织、自编译四大模块，
    提供统一的系统管理和协调接口。
    
    铁三角原则实现：
    - 信任原则：通过审计系统记录所有操作
    - 复利原则：通过持久化系统保存状态
    - 杠杆原则：通过配置系统驱动行为
    
    Example:
        >>> system = FourSelfSystem()
        >>> system.initialize()
        >>> system.health_check()
        >>> system.run_workflow(my_workflow)
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化四自系统
        
        Args:
            config_path: 配置文件路径，默认使用 ~/.temper/config.json
        """
        self._initialized = False
        self._config_path = config_path
        
        # 核心组件（延迟初始化）
        self._config = None
        self._audit_logger = None
        self._backup_manager = None
        self._rollback_manager = None
        self._state_manager = None
        self._health_checker = None
        self._adaptive_manager = None
        self._workflow_engine = None
        self._self_compiling = None
        
    @property
    def config(self):
        """获取配置管理器"""
        if self._config is None:
            from .config import get_config
            self._config = get_config(self._config_path)
        return self._config
    
    @property
    def audit_logger(self):
        """获取审计日志器"""
        if self._audit_logger is None:
            from .audit import get_audit_logger
            self._audit_logger = get_audit_logger()
        return self._audit_logger
    
    @property
    def backup_manager(self):
        """获取备份管理器"""
        if self._backup_manager is None:
            from .audit import get_backup_manager
            self._backup_manager = get_backup_manager()
        return self._backup_manager
    
    @property
    def rollback_manager(self):
        """获取回滚管理器"""
        if self._rollback_manager is None:
            from .audit import get_rollback_manager
            self._rollback_manager = get_rollback_manager()
        return self._rollback_manager
    
    @property
    def state_manager(self):
        """获取状态管理器"""
        if self._state_manager is None:
            from .persistence import get_state_manager
            self._state_manager = get_state_manager("four_self_system")
        return self._state_manager
    
    @property
    def health_checker(self):
        """获取健康检查器"""
        if self._health_checker is None:
            from .self_awareness import HealthChecker
            self._health_checker = HealthChecker()
        return self._health_checker
    
    @property
    def adaptive_manager(self):
        """获取自适应管理器"""
        if self._adaptive_manager is None:
            from .self_adaptive import get_global_manager
            self._adaptive_manager = get_global_manager()
        return self._adaptive_manager
    
    @property
    def workflow_engine(self):
        """获取工作流引擎"""
        if self._workflow_engine is None:
            from .self_organizing import WorkflowEngine
            self._workflow_engine = WorkflowEngine()
        return self._workflow_engine
    
    @property
    def self_compiling(self):
        """获取自编译模块"""
        if self._self_compiling is None:
            from .self_compiling import SelfCompilingModule
            self._self_compiling = SelfCompilingModule()
        return self._self_compiling
    
    def initialize(self) -> dict:
        """
        初始化四自系统
        
        Returns:
            Codong 风格结果
        """
        try:
            # 初始化配置系统
            config_result = self.config.load()
            if is_error(config_result):
                return config_result
            
            # 初始化审计系统
            from .audit import init_audit_system
            audit_result = init_audit_system()
            if is_error(audit_result):
                return audit_result
            
            # 初始化持久化系统
            self.state_manager.set("system.version", __version__)
            self.state_manager.set("system.initialized_at", 
                                   __import__('datetime').datetime.now().isoformat())
            
            # 记录初始化日志
            self.audit_logger.log(
                operation=AuditLogger.OP_SYSTEM_INIT,
                details={"version": __version__, "config_path": self._config_path}
            )
            
            self._initialized = True
            return ok({"status": "initialized", "version": __version__})
            
        except Exception as e:
            return err(ErrorCode.INITIALIZATION_ERROR, f"系统初始化失败: {str(e)}")
    
    def health_check(self, dependencies: dict = None) -> dict:
        """
        执行系统健康检查
        
        Args:
            dependencies: 依赖检查配置
            
        Returns:
            Codong 风格结果，包含健康报告
        """
        if not self._initialized:
            return err(ErrorCode.INITIALIZATION_ERROR, "系统未初始化")
        
        try:
            from .self_awareness import create_health_report
            return create_health_report(dependencies)
        except Exception as e:
            return err(ErrorCode.HEALTH_CHECK_ERROR, f"健康检查失败: {str(e)}")
    
    def adapt(self, metrics: dict = None) -> dict:
        """
        执行自适应调整
        
        Args:
            metrics: 性能指标
            
        Returns:
            Codong 风格结果
        """
        if not self._initialized:
            return err(ErrorCode.INITIALIZATION_ERROR, "系统未初始化")
        
        try:
            return self.adaptive_manager.adapt_all(metrics)
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"自适应调整失败: {str(e)}")
    
    def run_workflow(self, workflow, mode: str = "auto") -> dict:
        """
        执行工作流
        
        Args:
            workflow: 工作流对象或工作流定义
            mode: 执行模式 (serial/parallel/auto)
            
        Returns:
            Codong 风格结果
        """
        if not self._initialized:
            return err(ErrorCode.INITIALIZATION_ERROR, "系统未初始化")
        
        try:
            from .self_organizing import run_workflow as rw
            return rw(workflow, mode)
        except Exception as e:
            return err(ErrorCode.WORKFLOW_EXECUTION_ERROR, f"工作流执行失败: {str(e)}")
    
    def self_repair(self, target: str = None) -> dict:
        """
        执行自我修复
        
        Args:
            target: 修复目标（文件路径或模块名）
            
        Returns:
            Codong 风格结果
        """
        if not self._initialized:
            return err(ErrorCode.INITIALIZATION_ERROR, "系统未初始化")
        
        try:
            if target:
                return self.self_compiling.self_repair(target)
            else:
                # 系统级自修复
                health = self.health_check()
                if is_error(health):
                    return health
                
                report = unwrap(health)
                if report.status == "healthy":
                    return ok({"repaired": False, "reason": "系统健康，无需修复"})
                
                # 根据健康报告执行修复
                repairs = []
                for issue in report.issues:
                    if issue.get("auto_fixable"):
                        repair_result = self._auto_fix_issue(issue)
                        repairs.append({"issue": issue, "result": repair_result})
                
                return ok({"repaired": True, "repairs": repairs})
                
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"自我修复失败: {str(e)}")
    
    def _auto_fix_issue(self, issue: dict) -> dict:
        """自动修复单个问题"""
        issue_type = issue.get("type")
        
        if issue_type == "config_invalid":
            # 重置配置为默认值
            self.config.reset_to_defaults()
            return ok({"fixed": True, "action": "reset_config"})
        
        elif issue_type == "resource_exhausted":
            # 清理资源
            self.adaptive_manager.optimize_all()
            return ok({"fixed": True, "action": "optimize_resources"})
        
        return ok({"fixed": False, "reason": "无法自动修复"})
    
    def save_state(self) -> dict:
        """
        保存系统状态
        
        Returns:
            Codong 风格结果
        """
        if not self._initialized:
            return err(ErrorCode.INITIALIZATION_ERROR, "系统未初始化")
        
        try:
            return self.state_manager.save()
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"保存状态失败: {str(e)}")
    
    def load_state(self) -> dict:
        """
        加载系统状态
        
        Returns:
            Codong 风格结果
        """
        try:
            return self.state_manager.load()
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"加载状态失败: {str(e)}")
    
    def get_status(self) -> dict:
        """
        获取系统状态
        
        Returns:
            Codong 风格结果
        """
        try:
            status = {
                "initialized": self._initialized,
                "version": __version__,
                "components": {
                    "config": self._config is not None,
                    "audit": self._audit_logger is not None,
                    "state": self._state_manager is not None,
                    "health": self._health_checker is not None,
                    "adaptive": self._adaptive_manager is not None,
                    "workflow": self._workflow_engine is not None,
                    "compiling": self._self_compiling is not None,
                }
            }
            return ok(status)
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"获取状态失败: {str(e)}")
    
    def shutdown(self) -> dict:
        """
        关闭系统
        
        Returns:
            Codong 风格结果
        """
        try:
            # 保存状态
            self.save_state()
            
            # 记录关闭日志
            if self._audit_logger:
                self.audit_logger.log(
                    operation=AuditLogger.OP_SYSTEM_SHUTDOWN,
                    details={"version": __version__}
                )
            
            self._initialized = False
            return ok({"status": "shutdown"})
        except Exception as e:
            return err(ErrorCode.OPERATION_FAILED, f"关闭系统失败: {str(e)}")


# 全局系统实例
_global_system = None


def get_four_self_system(config_path: str = None) -> FourSelfSystem:
    """
    获取四自系统全局实例（单例模式）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        FourSelfSystem 实例
    """
    global _global_system
    if _global_system is None:
        _global_system = FourSelfSystem(config_path)
    return _global_system


def init_four_self_system(config_path: str = None) -> dict:
    """
    初始化四自系统（便捷函数）
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Codong 风格结果
    """
    system = get_four_self_system(config_path)
    return system.initialize()


# 导出四自系统
__all__ = [
    # 版本信息
    "__version__",
    
    # 错误处理
    "ok", "err", "is_error", "is_ok", "unwrap", "unwrap_or_raise",
    "map_result", "bind_result", "CodongError", "ErrorCode",
    "file_not_found", "file_read_error", "file_write_error",
    "permission_denied", "network_error", "timeout_error",
    "validation_error", "not_found",
    
    # 配置系统
    "Config", "ConfigValidator", "get_config",
    "config_get", "config_set", "config_save", "config_reload",
    
    # 审计系统
    "AuditLogger", "BackupManager", "RollbackManager",
    "init_audit_system", "get_audit_logger", "get_backup_manager", "get_rollback_manager",
    "audited_operation", "audited_context", "safe_file_write", "safe_file_delete",
    
    # 持久化系统
    "StateManager", "Snapshot", "Migration",
    "get_state_manager", "persist_get", "persist_set",
    "persist_save", "persist_load", "persist_restore",
    "create_full_backup", "restore_from_backup",
    
    # 自感知模块
    "ResourceMonitor", "DependencyChecker", "HealthChecker",
    "HealthStatus", "HealthReport", "quick_health_check",
    "create_health_report", "check_system_readiness",
    
    # 自适应模块
    "ParameterTuner", "PerformanceOptimizer", "RateLimiter",
    "ConfigHotUpdater", "AdaptiveManager", "PerformanceMetrics",
    "create_adaptive_manager", "get_global_manager",
    
    # 自组织模块
    "Workflow", "Task", "TaskExecutor", "DependencyResolver", "WorkflowEngine",
    "create_workflow", "run_workflow", "serial_tasks", "parallel_tasks",
    "conditional_workflow", "compose_workflows",
    
    # 自编译模块
    "CodeTemplate", "CodeGenerator", "SelfRepair", "HotLoader",
    "SelfCompilingModule", "compile_template", "generate_and_load",
    "self_compile", "enable_hot_reload",
    
    # 四自系统整合器
    "FourSelfSystem", "get_four_self_system", "init_four_self_system",
]
