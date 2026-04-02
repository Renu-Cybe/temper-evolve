"""
🧊 Temper Evolve v3.0 - 四自系统

AI 原生 Coding Agent，具备自感知、自适应、自组织、自编译能力

铁三角原则：
1. 信任原则：透明可审计，操作可回溯
2. 复利原则：能力持久化，状态可恢复
3. 杠杆原则：配置驱动，拒绝硬编码

四自系统：
1. 自感知：健康自检、状态监控、资源监控
2. 自适应：动态调参、性能优化、负载均衡
3. 自组织：工作流合成、任务编排、依赖管理
4. 自编译：自我修复、代码生成、热加载
"""

__version__ = "3.0.0"
__author__ = "Temper Team"

# 从 core 导入核心功能
from .core import (
    # 错误处理
    ok, err, is_ok, is_error, unwrap, unwrap_or_raise,
    CodongError, ErrorCode,
    # 四自系统
    FourSelfSystem, get_four_self_system, init_four_self_system,
    # 配置系统
    Config, ConfigValidator, get_config,
    # 审计系统
    AuditLogger, BackupManager, RollbackManager,
    init_audit_system, get_audit_logger, get_backup_manager, get_rollback_manager,
    audited_operation, audited_context, safe_file_write, safe_file_delete,
    # 持久化系统
    StateManager, Snapshot, Migration,
    get_state_manager, persist_get, persist_set,
    persist_save, persist_load, persist_restore,
    create_full_backup, restore_from_backup,
    # 自感知
    ResourceMonitor, DependencyChecker, HealthChecker,
    HealthStatus, HealthReport, quick_health_check,
    create_health_report, check_system_readiness,
    # 自适应
    ParameterTuner, PerformanceOptimizer, RateLimiter,
    ConfigHotUpdater, AdaptiveManager, PerformanceMetrics,
    create_adaptive_manager, get_global_manager,
    # 自组织
    Workflow, Task, TaskExecutor, DependencyResolver, WorkflowEngine,
    create_workflow, run_workflow, serial_tasks, parallel_tasks,
    conditional_workflow, compose_workflows,
    # 自编译
    CodeTemplate, CodeGenerator, SelfRepair, HotLoader,
    SelfCompilingModule, compile_template,
    self_compile, enable_hot_reload,
)

__all__ = [
    '__version__',
    # 错误处理
    'ok', 'err', 'is_ok', 'is_error', 'unwrap', 'unwrap_or_raise',
    'CodongError', 'ErrorCode',
    # 四自系统
    'FourSelfSystem', 'get_four_self_system', 'init_four_self_system',
    # 配置系统
    'Config', 'ConfigValidator', 'get_config',
    # 审计系统
    'AuditLogger', 'BackupManager', 'RollbackManager',
    'init_audit_system', 'get_audit_logger', 'get_backup_manager', 'get_rollback_manager',
    'audited_operation', 'audited_context', 'safe_file_write', 'safe_file_delete',
    # 持久化系统
    'StateManager', 'Snapshot', 'Migration',
    'get_state_manager', 'persist_get', 'persist_set',
    'persist_save', 'persist_load', 'persist_restore',
    'create_full_backup', 'restore_from_backup',
    # 自感知
    'ResourceMonitor', 'DependencyChecker', 'HealthChecker',
    'HealthStatus', 'HealthReport', 'quick_health_check',
    'create_health_report', 'check_system_readiness',
    # 自适应
    'ParameterTuner', 'PerformanceOptimizer', 'RateLimiter',
    'ConfigHotUpdater', 'AdaptiveManager', 'PerformanceMetrics',
    'create_adaptive_manager', 'get_global_manager',
    # 自组织
    'Workflow', 'Task', 'TaskExecutor', 'DependencyResolver', 'WorkflowEngine',
    'create_workflow', 'run_workflow', 'serial_tasks', 'parallel_tasks',
    'conditional_workflow', 'compose_workflows',
    # 自编译
    'CodeTemplate', 'CodeGenerator', 'SelfRepair', 'HotLoader',
    'SelfCompilingModule', 'compile_template',
    'self_compile', 'enable_hot_reload',
]
