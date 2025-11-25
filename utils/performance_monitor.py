#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控工具 - 废弃物AI识别指导投放系统
监控系统性能，包括CPU、内存、FPS等指标
"""

import time
import threading
import logging
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    process_memory_mb: float
    fps: float = 0.0
    frame_processing_time: float = 0.0
    detection_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'process_memory_mb': self.process_memory_mb,
            'fps': self.fps,
            'frame_processing_time': self.frame_processing_time,
            'detection_time': self.detection_time
        }


@dataclass
class PerformanceStats:
    """性能统计"""
    avg_cpu: float = 0.0
    max_cpu: float = 0.0
    avg_memory: float = 0.0
    max_memory: float = 0.0
    avg_fps: float = 0.0
    min_fps: float = 0.0
    avg_frame_time: float = 0.0
    max_frame_time: float = 0.0
    sample_count: int = 0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_samples: int = 1000, update_interval: float = 1.0):
        """
        初始化性能监控器
        
        Args:
            max_samples: 最大样本数
            update_interval: 更新间隔(秒)
        """
        self.max_samples = max_samples
        self.update_interval = update_interval
        self.logger = logging.getLogger(__name__)
        
        # 性能数据
        self.metrics_history: deque = deque(maxlen=max_samples)
        self.lock = threading.Lock()
        
        # 监控状态
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 性能计数器
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        
        # 时间测量
        self.frame_start_time = 0.0
        self.detection_start_time = 0.0
        
        self.logger.info("性能监控器初始化完成")
    
    def start_monitoring(self):
        """开始性能监控"""
        with self.lock:
            if self.monitoring:
                self.logger.warning("性能监控已在运行")
                return
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="PerformanceMonitor"
            )
            self.monitor_thread.start()
        
        self.logger.info("性能监控已启动")
    
    def stop_monitoring(self):
        """停止性能监控"""
        with self.lock:
            self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.logger.info("性能监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self._collect_metrics()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"性能监控异常: {e}")
                time.sleep(self.update_interval)
    
    def _collect_metrics(self):
        """收集性能指标"""
        try:
            # 获取系统指标
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # 获取进程指标
            process = psutil.Process()
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 创建性能指标
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                process_memory_mb=process_memory,
                fps=self.current_fps,
                frame_processing_time=0.0,  # 由外部设置
                detection_time=0.0  # 由外部设置
            )
            
            # 存储指标
            with self.lock:
                self.metrics_history.append(metrics)
            
        except Exception as e:
            self.logger.error(f"收集性能指标失败: {e}")
    
    def start_frame_timing(self):
        """开始帧处理计时"""
        self.frame_start_time = time.time()
    
    def end_frame_timing(self):
        """结束帧处理计时"""
        if self.frame_start_time > 0:
            frame_time = time.time() - self.frame_start_time
            self._update_frame_metrics(frame_time)
            self.frame_start_time = 0.0
    
    def start_detection_timing(self):
        """开始检测计时"""
        self.detection_start_time = time.time()
    
    def end_detection_timing(self) -> float:
        """结束检测计时"""
        if self.detection_start_time > 0:
            detection_time = time.time() - self.detection_start_time
            self.detection_start_time = 0.0
            return detection_time
        return 0.0
    
    def _update_frame_metrics(self, frame_time: float):
        """更新帧相关指标"""
        self.frame_count += 1
        current_time = time.time()
        
        # 计算FPS
        time_diff = current_time - self.last_fps_time
        if time_diff >= 1.0:  # 每秒更新一次FPS
            self.current_fps = self.frame_count / time_diff
            self.frame_count = 0
            self.last_fps_time = current_time
        
        # 更新最新的指标
        with self.lock:
            if self.metrics_history:
                latest_metrics = self.metrics_history[-1]
                latest_metrics.frame_processing_time = frame_time
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标"""
        with self.lock:
            if self.metrics_history:
                return self.metrics_history[-1]
        return None
    
    def get_performance_stats(self) -> PerformanceStats:
        """获取性能统计"""
        with self.lock:
            if not self.metrics_history:
                return PerformanceStats()
            
            metrics_list = list(self.metrics_history)
        
        # 计算统计数据
        cpu_values = [m.cpu_percent for m in metrics_list]
        memory_values = [m.memory_percent for m in metrics_list]
        fps_values = [m.fps for m in metrics_list if m.fps > 0]
        frame_time_values = [m.frame_processing_time for m in metrics_list if m.frame_processing_time > 0]
        
        stats = PerformanceStats(
            sample_count=len(metrics_list)
        )
        
        if cpu_values:
            stats.avg_cpu = sum(cpu_values) / len(cpu_values)
            stats.max_cpu = max(cpu_values)
        
        if memory_values:
            stats.avg_memory = sum(memory_values) / len(memory_values)
            stats.max_memory = max(memory_values)
        
        if fps_values:
            stats.avg_fps = sum(fps_values) / len(fps_values)
            stats.min_fps = min(fps_values)
        
        if frame_time_values:
            stats.avg_frame_time = sum(frame_time_values) / len(frame_time_values)
            stats.max_frame_time = max(frame_time_values)
        
        return stats
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        current_metrics = self.get_current_metrics()
        stats = self.get_performance_stats()
        
        report = {
            "current": current_metrics.to_dict() if current_metrics else {},
            "statistics": {
                "avg_cpu_percent": stats.avg_cpu,
                "max_cpu_percent": stats.max_cpu,
                "avg_memory_percent": stats.avg_memory,
                "max_memory_percent": stats.max_memory,
                "avg_fps": stats.avg_fps,
                "min_fps": stats.min_fps,
                "avg_frame_time_ms": stats.avg_frame_time * 1000,
                "max_frame_time_ms": stats.max_frame_time * 1000,
                "sample_count": stats.sample_count
            },
            "health": {
                "cpu_healthy": stats.avg_cpu < 80,
                "memory_healthy": stats.avg_memory < 85,
                "fps_healthy": stats.avg_fps > 15,
                "frame_time_healthy": stats.avg_frame_time < 0.1
            }
        }
        
        return report
    
    def clear_history(self):
        """清空历史数据"""
        with self.lock:
            self.metrics_history.clear()
        self.logger.info("性能历史数据已清空")
    
    def __del__(self):
        """析构函数"""
        self.stop_monitoring()


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
