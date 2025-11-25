#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存管理工具 - 废弃物AI识别指导投放系统
优化内存使用，防止内存泄漏
"""

import gc
import psutil
import logging
import threading
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MemoryStats:
    """内存统计信息"""
    total_memory: float  # 总内存 (MB)
    available_memory: float  # 可用内存 (MB)
    used_memory: float  # 已用内存 (MB)
    memory_percent: float  # 内存使用百分比
    process_memory: float  # 进程内存 (MB)


class MemoryManager:
    """内存管理器"""
    
    def __init__(self, memory_limit_mb: int = 1024, check_interval: float = 30.0):
        """
        初始化内存管理器
        
        Args:
            memory_limit_mb: 内存限制 (MB)
            check_interval: 检查间隔 (秒)
        """
        self.memory_limit_mb = memory_limit_mb
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        
        # 监控状态
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # 统计信息
        self.stats_history = []
        self.max_history_size = 100
        
        # 回调函数
        self.memory_warning_callback = None
        self.memory_critical_callback = None
        
        self.logger.info(f"内存管理器初始化完成，限制: {memory_limit_mb}MB")
    
    def get_memory_stats(self) -> MemoryStats:
        """获取当前内存统计信息"""
        try:
            # 系统内存信息
            memory = psutil.virtual_memory()
            
            # 进程内存信息
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            stats = MemoryStats(
                total_memory=memory.total / 1024 / 1024,
                available_memory=memory.available / 1024 / 1024,
                used_memory=memory.used / 1024 / 1024,
                memory_percent=memory.percent,
                process_memory=process_memory
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取内存统计失败: {e}")
            return MemoryStats(0, 0, 0, 0, 0)
    
    def check_memory_usage(self) -> bool:
        """
        检查内存使用情况
        
        Returns:
            bool: 内存使用是否正常
        """
        stats = self.get_memory_stats()
        
        # 记录统计信息
        with self.lock:
            self.stats_history.append(stats)
            if len(self.stats_history) > self.max_history_size:
                self.stats_history.pop(0)
        
        # 检查进程内存使用
        if stats.process_memory > self.memory_limit_mb:
            self.logger.warning(
                f"进程内存使用超限: {stats.process_memory:.1f}MB > {self.memory_limit_mb}MB"
            )
            
            # 触发内存清理
            self.cleanup_memory()
            
            # 调用回调函数
            if self.memory_critical_callback:
                try:
                    self.memory_critical_callback(stats)
                except Exception as e:
                    self.logger.error(f"内存临界回调执行失败: {e}")
            
            return False
        
        # 检查系统内存使用
        elif stats.memory_percent > 85:
            self.logger.warning(f"系统内存使用过高: {stats.memory_percent:.1f}%")
            
            if self.memory_warning_callback:
                try:
                    self.memory_warning_callback(stats)
                except Exception as e:
                    self.logger.error(f"内存警告回调执行失败: {e}")
        
        return True
    
    def cleanup_memory(self):
        """清理内存"""
        try:
            self.logger.info("开始内存清理...")
            
            # 强制垃圾回收
            collected = gc.collect()
            self.logger.info(f"垃圾回收完成，清理对象数: {collected}")
            
            # 获取清理后的内存状态
            stats = self.get_memory_stats()
            self.logger.info(f"清理后进程内存: {stats.process_memory:.1f}MB")
            
        except Exception as e:
            self.logger.error(f"内存清理失败: {e}")
    
    def start_monitoring(self):
        """开始内存监控"""
        with self.lock:
            if self.monitoring:
                self.logger.warning("内存监控已在运行")
                return
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="MemoryMonitor"
            )
            self.monitor_thread.start()
            
        self.logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        with self.lock:
            self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("内存监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self.check_memory_usage()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"内存监控异常: {e}")
                time.sleep(self.check_interval)
    
    def get_memory_report(self) -> Dict[str, Any]:
        """获取内存报告"""
        with self.lock:
            if not self.stats_history:
                return {"error": "无统计数据"}
            
            current_stats = self.stats_history[-1]
            
            # 计算平均值
            avg_process_memory = sum(s.process_memory for s in self.stats_history) / len(self.stats_history)
            max_process_memory = max(s.process_memory for s in self.stats_history)
            
            return {
                "current": {
                    "process_memory_mb": current_stats.process_memory,
                    "system_memory_percent": current_stats.memory_percent,
                    "available_memory_mb": current_stats.available_memory
                },
                "statistics": {
                    "average_process_memory_mb": avg_process_memory,
                    "max_process_memory_mb": max_process_memory,
                    "memory_limit_mb": self.memory_limit_mb,
                    "samples_count": len(self.stats_history)
                },
                "status": {
                    "memory_usage_normal": current_stats.process_memory < self.memory_limit_mb,
                    "system_memory_healthy": current_stats.memory_percent < 85,
                    "monitoring_active": self.monitoring
                }
            }
    
    def set_memory_warning_callback(self, callback):
        """设置内存警告回调函数"""
        self.memory_warning_callback = callback
    
    def set_memory_critical_callback(self, callback):
        """设置内存临界回调函数"""
        self.memory_critical_callback = callback
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()


# 全局内存管理器实例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(memory_limit_mb: int = 1024) -> MemoryManager:
    """获取全局内存管理器实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(memory_limit_mb)
    return _memory_manager


def cleanup_memory():
    """便捷的内存清理函数"""
    manager = get_memory_manager()
    manager.cleanup_memory()


def get_memory_stats() -> MemoryStats:
    """便捷的内存统计函数"""
    manager = get_memory_manager()
    return manager.get_memory_stats()
