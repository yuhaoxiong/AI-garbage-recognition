#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理装饰器 - 废弃物AI识别指导投放系统
提供统一的异常处理和错误恢复机制
"""

import functools
import logging
import traceback
import time
from typing import Any, Callable, Optional, Union, Type
from enum import Enum


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"          # 低级错误，可以忽略
    MEDIUM = "medium"    # 中级错误，需要记录但不影响主要功能
    HIGH = "high"        # 高级错误，影响功能但系统可继续运行
    CRITICAL = "critical" # 严重错误，可能导致系统崩溃


class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.last_error_time = {}
    
    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        max_retries: int = 0,
        retry_delay: float = 1.0
    ) -> bool:
        """
        处理异常
        
        Args:
            exception: 异常对象
            context: 上下文信息
            severity: 错误严重程度
            max_retries: 最大重试次数
            retry_delay: 重试延迟
            
        Returns:
            bool: 是否成功处理
        """
        error_key = f"{type(exception).__name__}:{context}"
        current_time = time.time()
        
        # 更新错误计数
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_time[error_key] = current_time
        
        # 记录错误
        error_msg = f"[{severity.value.upper()}] {context}: {str(exception)}"
        
        if severity == ErrorSeverity.LOW:
            self.logger.debug(error_msg)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_msg)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(error_msg)
        else:  # CRITICAL
            self.logger.critical(error_msg)
            self.logger.critical(f"详细错误信息:\n{traceback.format_exc()}")
        
        # 检查错误频率
        if self._is_error_frequent(error_key):
            self.logger.warning(f"错误频繁发生: {error_key}")
            return False
        
        return True
    
    def _is_error_frequent(self, error_key: str, threshold: int = 5, time_window: float = 60.0) -> bool:
        """检查错误是否频繁发生"""
        count = self.error_counts.get(error_key, 0)
        last_time = self.last_error_time.get(error_key, 0)
        current_time = time.time()
        
        if count >= threshold and (current_time - last_time) < time_window:
            return True
        
        return False


# 全局异常处理器
_global_handler = ExceptionHandler()


def safe_execute(
    func: Callable,
    default_value: Any = None,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    max_retries: int = 0,
    retry_delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        default_value: 出错时的默认返回值
        context: 上下文信息
        severity: 错误严重程度
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        exceptions: 要捕获的异常类型
        
    Returns:
        函数执行结果或默认值
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            _global_handler.handle_exception(e, context, severity)
            
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            else:
                return default_value


def exception_handler(
    default_value: Any = None,
    context: str = "",
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    max_retries: int = 0,
    retry_delay: float = 1.0,
    exceptions: tuple = (Exception,),
    reraise: bool = False
):
    """
    异常处理装饰器
    
    Args:
        default_value: 出错时的默认返回值
        context: 上下文信息
        severity: 错误严重程度
        max_retries: 最大重试次数
        retry_delay: 重试延迟
        exceptions: 要捕获的异常类型
        reraise: 是否重新抛出异常
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_context = context or f"{func.__module__}.{func.__name__}"
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    _global_handler.handle_exception(e, func_context, severity)
                    
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    else:
                        if reraise:
                            raise
                        return default_value
            
        return wrapper
    return decorator


def critical_section(
    context: str = "",
    timeout: float = 30.0,
    cleanup_func: Optional[Callable] = None
):
    """
    关键代码段装饰器
    
    Args:
        context: 上下文信息
        timeout: 超时时间
        cleanup_func: 清理函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_context = context or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                # 检查超时
                if timeout > 0:
                    def check_timeout():
                        if time.time() - start_time > timeout:
                            raise TimeoutError(f"函数执行超时: {func_context}")
                    
                    # 这里可以添加超时检查逻辑
                
                return func(*args, **kwargs)
                
            except Exception as e:
                _global_handler.handle_exception(
                    e, 
                    f"关键代码段错误: {func_context}", 
                    ErrorSeverity.CRITICAL
                )
                
                # 执行清理
                if cleanup_func:
                    try:
                        cleanup_func()
                    except Exception as cleanup_error:
                        _global_handler.handle_exception(
                            cleanup_error,
                            f"清理函数错误: {func_context}",
                            ErrorSeverity.HIGH
                        )
                
                raise
            
        return wrapper
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    失败重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟
        backoff_factor: 退避因子
        exceptions: 要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = retry_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    
                    _global_handler.handle_exception(
                        e,
                        f"重试 {attempt + 1}/{max_retries}: {func.__name__}",
                        ErrorSeverity.MEDIUM
                    )
                    
                    time.sleep(delay)
                    delay *= backoff_factor
            
        return wrapper
    return decorator


# 便捷的装饰器别名
safe = exception_handler
critical = critical_section
retry = retry_on_failure
