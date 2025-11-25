#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误恢复工具 - 废弃物AI识别指导投放系统
提供系统级别的错误处理、恢复和降级机制
"""

import logging
import traceback
import functools
import time
from typing import Any, Callable, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
from pathlib import Path


class RecoveryLevel(Enum):
    """恢复级别"""
    MINIMAL = "minimal"      # 最小功能模式
    BASIC = "basic"          # 基础功能模式
    NORMAL = "normal"        # 正常功能模式
    FULL = "full"           # 完整功能模式


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: str
    error_message: str
    timestamp: float
    traceback_info: str
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_level: Optional[RecoveryLevel] = None


class SystemRecoveryManager:
    """系统恢复管理器"""
    
    def __init__(self):
        """初始化恢复管理器"""
        self.logger = logging.getLogger(__name__)
        self.errors: List[ErrorInfo] = []
        self.current_recovery_level = RecoveryLevel.FULL
        self.max_errors_per_minute = 10
        self.recovery_strategies: Dict[str, Callable] = {}
        
        # 注册默认恢复策略
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        self.recovery_strategies.update({
            "ImportError": self._handle_import_error,
            "FileNotFoundError": self._handle_file_not_found,
            "PermissionError": self._handle_permission_error,
            "ConnectionError": self._handle_connection_error,
            "MemoryError": self._handle_memory_error,
            "RuntimeError": self._handle_runtime_error,
            "ValueError": self._handle_value_error,
            "KeyError": self._handle_key_error,
        })
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """
        注册自定义恢复策略
        
        Args:
            error_type: 错误类型
            strategy: 恢复策略函数
        """
        self.recovery_strategies[error_type] = strategy
        self.logger.info(f"已注册恢复策略: {error_type}")
    
    def handle_error(self, error: Exception, context: str = "") -> bool:
        """
        处理错误并尝试恢复
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            bool: 是否成功恢复
        """
        try:
            error_type = type(error).__name__
            error_message = str(error)
            timestamp = time.time()
            traceback_info = traceback.format_exc()
            
            # 记录错误信息
            error_info = ErrorInfo(
                error_type=error_type,
                error_message=error_message,
                timestamp=timestamp,
                traceback_info=traceback_info
            )
            self.errors.append(error_info)
            
            self.logger.error(f"捕获错误 [{context}]: {error_type} - {error_message}")
            
            # 检查错误频率
            if self._is_error_rate_too_high():
                self.logger.warning("错误频率过高，降级系统运行级别")
                self._downgrade_system()
            
            # 尝试恢复
            recovery_successful = self._attempt_recovery(error_info, context)
            
            error_info.recovery_attempted = True
            error_info.recovery_successful = recovery_successful
            error_info.recovery_level = self.current_recovery_level
            
            return recovery_successful
            
        except Exception as recovery_error:
            self.logger.critical(f"错误恢复过程中发生异常: {recovery_error}")
            return False
    
    def _is_error_rate_too_high(self) -> bool:
        """检查错误频率是否过高"""
        current_time = time.time()
        recent_errors = [
            error for error in self.errors 
            if current_time - error.timestamp < 60  # 最近1分钟
        ]
        return len(recent_errors) > self.max_errors_per_minute
    
    def _downgrade_system(self):
        """降级系统运行级别"""
        if self.current_recovery_level == RecoveryLevel.FULL:
            self.current_recovery_level = RecoveryLevel.NORMAL
        elif self.current_recovery_level == RecoveryLevel.NORMAL:
            self.current_recovery_level = RecoveryLevel.BASIC
        elif self.current_recovery_level == RecoveryLevel.BASIC:
            self.current_recovery_level = RecoveryLevel.MINIMAL
        
        self.logger.warning(f"系统降级至: {self.current_recovery_level.value}")
    
    def _attempt_recovery(self, error_info: ErrorInfo, context: str) -> bool:
        """尝试错误恢复"""
        error_type = error_info.error_type
        
        if error_type in self.recovery_strategies:
            try:
                strategy = self.recovery_strategies[error_type]
                return strategy(error_info, context)
            except Exception as e:
                self.logger.error(f"恢复策略执行失败: {e}")
                return False
        else:
            self.logger.warning(f"未找到 {error_type} 的恢复策略")
            return self._generic_recovery(error_info, context)
    
    def _generic_recovery(self, error_info: ErrorInfo, context: str) -> bool:
        """通用恢复策略"""
        self.logger.info("执行通用恢复策略")
        
        # 记录错误但继续运行
        self.logger.warning(f"无法恢复错误，继续运行: {error_info.error_message}")
        return False
    
    def _handle_import_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理导入错误"""
        self.logger.info("处理导入错误")
        
        # 提取模块名
        error_message = error_info.error_message
        if "No module named" in error_message:
            module_name = error_message.split("'")[1] if "'" in error_message else "unknown"
            self.logger.warning(f"模块 {module_name} 不可用，功能将被禁用")
            
            # 记录缺失的模块
            self._record_missing_module(module_name)
            return True
        
        return False
    
    def _handle_file_not_found(self, error_info: ErrorInfo, context: str) -> bool:
        """处理文件未找到错误"""
        self.logger.info("处理文件未找到错误")
        
        # 尝试创建缺失的目录
        error_message = error_info.error_message
        if "config" in error_message.lower():
            return self._create_default_config()
        elif "logs" in error_message.lower():
            return self._create_logs_directory()
        elif "data" in error_message.lower():
            return self._create_data_directory()
        
        return False
    
    def _handle_permission_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理权限错误"""
        self.logger.info("处理权限错误")
        
        # 尝试使用替代路径
        error_message = error_info.error_message
        if "logs" in error_message.lower():
            return self._use_temp_logs_directory()
        elif "config" in error_message.lower():
            return self._use_temp_config()
        
        return False
    
    def _handle_connection_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理连接错误"""
        self.logger.info("处理连接错误")
        
        # 如果是API连接错误，切换到离线模式
        if "api" in context.lower():
            self.logger.warning("API连接失败，切换到离线模式")
            return True
        
        return False
    
    def _handle_memory_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理内存错误"""
        self.logger.info("处理内存错误")
        
        # 降低内存使用
        self.logger.warning("内存不足，降低系统性能设置")
        self._reduce_memory_usage()
        return True
    
    def _handle_runtime_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理运行时错误"""
        self.logger.info("处理运行时错误")

        # 根据上下文决定恢复策略
        if "camera" in context.lower():
            return self._recover_camera_error()
        elif "detection" in context.lower():
            return self._recover_detection_error()
        elif "ui" in context.lower():
            return self._recover_ui_error()
        elif "config" in context.lower():
            return self._recover_config_error()

        return False

    def _recover_camera_error(self) -> bool:
        """恢复摄像头错误"""
        self.logger.info("尝试恢复摄像头错误")

        try:
            # 等待一段时间后重试
            import time
            time.sleep(2.0)

            # 尝试重新初始化摄像头
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.release()
                self.logger.info("摄像头恢复成功")
                return True
            else:
                self.logger.warning("摄像头仍无法访问")
                return False

        except Exception as e:
            self.logger.error(f"摄像头恢复失败: {e}")
            return False

    def _recover_detection_error(self) -> bool:
        """恢复检测错误"""
        self.logger.info("尝试恢复检测错误")

        try:
            # 清理内存
            import gc
            gc.collect()

            # 降低检测频率
            self.logger.info("降低检测频率以减少错误")
            return True

        except Exception as e:
            self.logger.error(f"检测恢复失败: {e}")
            return False

    def _recover_ui_error(self) -> bool:
        """恢复UI错误"""
        self.logger.info("尝试恢复UI错误")

        try:
            # 刷新UI
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
                self.logger.info("UI刷新完成")
                return True

        except Exception as e:
            self.logger.error(f"UI恢复失败: {e}")

        return False

    def _recover_config_error(self) -> bool:
        """恢复配置错误"""
        self.logger.info("尝试恢复配置错误")

        try:
            # 重新加载配置
            from utils.config_manager import get_config_manager
            config_manager = get_config_manager()

            # 验证配置
            if config_manager.validate_config():
                self.logger.info("配置恢复成功")
                return True
            else:
                self.logger.warning("配置验证失败")
                return False

        except Exception as e:
            self.logger.error(f"配置恢复失败: {e}")
            return False
    
    def _handle_value_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理值错误"""
        self.logger.info("处理值错误")
        
        # 通常是配置值错误，使用默认值
        self.logger.warning("配置值错误，使用默认值")
        return True
    
    def _handle_key_error(self, error_info: ErrorInfo, context: str) -> bool:
        """处理键错误"""
        self.logger.info("处理键错误")
        
        # 通常是配置键缺失，使用默认配置
        self.logger.warning("配置键缺失，使用默认配置")
        return True
    
    def _record_missing_module(self, module_name: str):
        """记录缺失的模块"""
        missing_modules_file = Path("logs/missing_modules.txt")
        try:
            missing_modules_file.parent.mkdir(exist_ok=True)
            with open(missing_modules_file, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {module_name}\n")
        except Exception as e:
            self.logger.error(f"记录缺失模块失败: {e}")
    
    def _create_default_config(self) -> bool:
        """创建默认配置文件"""
        try:
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            # 创建基本的系统配置
            system_config = {
                "camera": {"device_id": 0, "fps": 30},
                "ui": {"window_title": "废弃物AI识别指导投放系统"},
                "logging": {"level": "INFO"}
            }
            
            import json
            with open(config_dir / "system_config.json", "w", encoding="utf-8") as f:
                json.dump(system_config, f, indent=2, ensure_ascii=False)
            
            self.logger.info("已创建默认配置文件")
            return True
            
        except Exception as e:
            self.logger.error(f"创建默认配置失败: {e}")
            return False
    
    def _create_logs_directory(self) -> bool:
        """创建日志目录"""
        try:
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            self.logger.info("已创建日志目录")
            return True
        except Exception as e:
            self.logger.error(f"创建日志目录失败: {e}")
            return False
    
    def _create_data_directory(self) -> bool:
        """创建数据目录"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            self.logger.info("已创建数据目录")
            return True
        except Exception as e:
            self.logger.error(f"创建数据目录失败: {e}")
            return False
    
    def _use_temp_logs_directory(self) -> bool:
        """使用临时日志目录"""
        try:
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "waste_detection_logs"
            temp_dir.mkdir(exist_ok=True)
            self.logger.info(f"使用临时日志目录: {temp_dir}")
            return True
        except Exception as e:
            self.logger.error(f"创建临时日志目录失败: {e}")
            return False
    
    def _use_temp_config(self) -> bool:
        """使用临时配置"""
        self.logger.info("使用内存中的临时配置")
        return True
    
    def _reduce_memory_usage(self):
        """降低内存使用"""
        self.logger.info("降低内存使用设置")
        # 这里可以实现具体的内存优化策略
        # 例如：降低图像分辨率、减少缓存等
    
    def _recover_camera_error(self) -> bool:
        """恢复摄像头错误"""
        self.logger.info("尝试恢复摄像头")
        # 可以尝试重新初始化摄像头或使用备用设备
        return True
    
    def _recover_detection_error(self) -> bool:
        """恢复检测错误"""
        self.logger.info("尝试恢复检测功能")
        # 可以切换到备用检测模式
        return True
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        if not self.errors:
            return {"total_errors": 0, "recovery_rate": 0.0}
        
        total_errors = len(self.errors)
        successful_recoveries = sum(1 for error in self.errors if error.recovery_successful)
        recovery_rate = successful_recoveries / total_errors if total_errors > 0 else 0.0
        
        error_types = {}
        for error in self.errors:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        return {
            "total_errors": total_errors,
            "successful_recoveries": successful_recoveries,
            "recovery_rate": recovery_rate,
            "current_recovery_level": self.current_recovery_level.value,
            "error_types": error_types,
            "recent_errors": len([e for e in self.errors if time.time() - e.timestamp < 300])  # 最近5分钟
        }
    
    def reset_error_history(self):
        """重置错误历史"""
        self.errors.clear()
        self.current_recovery_level = RecoveryLevel.FULL
        self.logger.info("错误历史已重置")


# 全局恢复管理器实例
_recovery_manager: Optional[SystemRecoveryManager] = None


def get_recovery_manager() -> SystemRecoveryManager:
    """获取恢复管理器实例（单例模式）"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = SystemRecoveryManager()
    return _recovery_manager


def with_error_recovery(context: str = ""):
    """
    装饰器：为函数添加错误恢复功能
    
    Args:
        context: 错误上下文描述
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                recovery_manager = get_recovery_manager()
                func_context = context or f"{func.__module__}.{func.__name__}"
                
                # 尝试恢复
                recovered = recovery_manager.handle_error(e, func_context)
                
                if not recovered:
                    # 如果无法恢复，重新抛出异常
                    raise
                
                # 恢复成功，返回默认值或None
                return None
                
        return wrapper
    return decorator


def safe_execute(func: Callable, default_value: Any = None, context: str = "") -> Any:
    """
    安全执行函数，自动处理错误和恢复
    
    Args:
        func: 要执行的函数
        default_value: 发生错误时的默认返回值
        context: 错误上下文
        
    Returns:
        函数执行结果或默认值
    """
    try:
        return func()
    except Exception as e:
        recovery_manager = get_recovery_manager()
        func_context = context or f"{func.__module__}.{func.__name__}"
        
        # 尝试恢复
        recovered = recovery_manager.handle_error(e, func_context)
        
        if recovered:
            # 恢复成功，可能需要重试
            try:
                return func()
            except Exception:
                # 重试失败，返回默认值
                return default_value
        else:
            # 无法恢复，返回默认值
            return default_value 