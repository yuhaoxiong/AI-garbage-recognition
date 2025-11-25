#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的使用示例 - 废弃物AI识别指导投放系统
展示如何使用新的优化功能
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入优化后的模块
from utils.memory_manager import get_memory_manager
from utils.performance_monitor import get_performance_monitor
from utils.exception_handler import safe, critical, retry, ErrorSeverity
from utils.config_manager import get_config_manager
from utils.error_recovery import get_recovery_manager


class OptimizedWasteDetectionExample:
    """优化后的废弃物检测示例"""
    
    def __init__(self):
        """初始化示例"""
        self.logger = logging.getLogger(__name__)
        
        # 初始化性能监控
        self.memory_manager = get_memory_manager(512)  # 512MB限制
        self.performance_monitor = get_performance_monitor()
        
        # 初始化配置和错误恢复
        self.config_manager = get_config_manager()
        self.recovery_manager = get_recovery_manager()
        
        self.logger.info("优化示例初始化完成")
    
    def start_monitoring(self):
        """启动监控系统"""
        try:
            # 启动内存监控
            self.memory_manager.start_monitoring()
            
            # 设置内存回调
            self.memory_manager.set_memory_warning_callback(self._on_memory_warning)
            self.memory_manager.set_memory_critical_callback(self._on_memory_critical)
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            self.logger.info("监控系统启动成功")
            
        except Exception as e:
            self.logger.error(f"启动监控系统失败: {e}")
    
    def _on_memory_warning(self, stats):
        """内存警告回调"""
        self.logger.warning(f"内存使用警告: {stats.memory_percent:.1f}%")
        
        # 执行轻量级清理
        self.memory_manager.cleanup_memory()
    
    def _on_memory_critical(self, stats):
        """内存临界回调"""
        self.logger.critical(f"内存使用临界: {stats.process_memory:.1f}MB")
        
        # 执行紧急清理
        self.memory_manager.cleanup_memory()
        
        # 降低系统性能设置
        self._reduce_performance_settings()
    
    def _reduce_performance_settings(self):
        """降低性能设置"""
        try:
            # 降低FPS
            self.config_manager.update_config('system', 'camera.fps', 15)
            
            # 减少检测频率
            self.config_manager.update_config('system', 'ai_detection.detection_interval', 0.2)
            
            self.logger.info("已降低性能设置以节省内存")
            
        except Exception as e:
            self.logger.error(f"降低性能设置失败: {e}")
    
    @safe(default_value=None, context="摄像头初始化", severity=ErrorSeverity.HIGH)
    def initialize_camera(self):
        """安全的摄像头初始化"""
        import cv2
        
        self.logger.info("初始化摄像头...")
        
        # 模拟可能失败的摄像头初始化
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            raise RuntimeError("无法打开摄像头")
        
        # 设置摄像头参数
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.logger.info("摄像头初始化成功")
        return cap
    
    @critical(context="AI模型加载", cleanup_func=lambda: logging.info("清理AI模型资源"))
    def load_ai_model(self):
        """关键的AI模型加载"""
        self.logger.info("加载AI模型...")
        
        # 模拟模型加载过程
        time.sleep(2)
        
        # 模拟可能的加载失败
        import random
        if random.random() < 0.1:  # 10%概率失败
            raise RuntimeError("AI模型加载失败")
        
        self.logger.info("AI模型加载成功")
        return "mock_model"
    
    @retry(max_retries=3, retry_delay=1.0, backoff_factor=2.0)
    def api_call_with_retry(self, data):
        """带重试的API调用"""
        self.logger.info("调用API...")
        
        # 模拟API调用
        import random
        if random.random() < 0.3:  # 30%概率失败
            raise ConnectionError("API连接失败")
        
        self.logger.info("API调用成功")
        return {"result": "success", "data": data}
    
    def simulate_detection_loop(self, duration: int = 30):
        """模拟检测循环"""
        self.logger.info(f"开始模拟检测循环，持续{duration}秒")
        
        start_time = time.time()
        frame_count = 0
        
        try:
            # 初始化摄像头
            cap = self.initialize_camera()
            if cap is None:
                self.logger.error("摄像头初始化失败，无法继续")
                return
            
            # 加载AI模型
            model = self.load_ai_model()
            
            while time.time() - start_time < duration:
                # 开始帧处理计时
                self.performance_monitor.start_frame_timing()
                
                try:
                    # 模拟读取帧
                    ret, frame = cap.read()
                    if not ret:
                        self.logger.warning("读取帧失败")
                        continue
                    
                    # 模拟AI检测
                    self.performance_monitor.start_detection_timing()
                    
                    # 模拟检测处理时间
                    time.sleep(0.05)  # 50ms处理时间
                    
                    detection_time = self.performance_monitor.end_detection_timing()
                    
                    # 模拟API调用（偶尔）
                    if frame_count % 30 == 0:  # 每30帧调用一次
                        try:
                            result = self.api_call_with_retry({"frame": frame_count})
                            self.logger.debug(f"API调用结果: {result}")
                        except Exception as e:
                            self.logger.warning(f"API调用最终失败: {e}")
                    
                    frame_count += 1
                    
                except Exception as e:
                    self.logger.error(f"帧处理错误: {e}")
                
                finally:
                    # 结束帧处理计时
                    self.performance_monitor.end_frame_timing()
                
                # 控制帧率
                time.sleep(1.0 / 30)  # 30 FPS
            
            # 清理资源
            cap.release()
            
        except Exception as e:
            self.logger.error(f"检测循环异常: {e}")
        
        self.logger.info(f"检测循环结束，处理了{frame_count}帧")
    
    def get_performance_report(self):
        """获取性能报告"""
        # 获取性能报告
        perf_report = self.performance_monitor.get_performance_report()
        memory_report = self.memory_manager.get_memory_report()
        
        print("\n" + "="*50)
        print("性能报告")
        print("="*50)
        
        # 当前状态
        current = perf_report.get('current', {})
        print(f"当前CPU使用率: {current.get('cpu_percent', 0):.1f}%")
        print(f"当前内存使用率: {current.get('memory_percent', 0):.1f}%")
        print(f"当前FPS: {current.get('fps', 0):.1f}")
        
        # 统计信息
        stats = perf_report.get('statistics', {})
        print(f"\n平均CPU使用率: {stats.get('avg_cpu_percent', 0):.1f}%")
        print(f"最大CPU使用率: {stats.get('max_cpu_percent', 0):.1f}%")
        print(f"平均内存使用率: {stats.get('avg_memory_percent', 0):.1f}%")
        print(f"平均FPS: {stats.get('avg_fps', 0):.1f}")
        print(f"最小FPS: {stats.get('min_fps', 0):.1f}")
        print(f"平均帧处理时间: {stats.get('avg_frame_time_ms', 0):.1f}ms")
        
        # 健康状态
        health = perf_report.get('health', {})
        print(f"\nCPU健康: {'✅' if health.get('cpu_healthy', False) else '❌'}")
        print(f"内存健康: {'✅' if health.get('memory_healthy', False) else '❌'}")
        print(f"FPS健康: {'✅' if health.get('fps_healthy', False) else '❌'}")
        
        # 内存报告
        memory_current = memory_report.get('current', {})
        print(f"\n当前进程内存: {memory_current.get('process_memory_mb', 0):.1f}MB")
        print(f"系统可用内存: {memory_current.get('available_memory_mb', 0):.1f}MB")
        
        memory_stats = memory_report.get('statistics', {})
        print(f"平均进程内存: {memory_stats.get('average_process_memory_mb', 0):.1f}MB")
        print(f"最大进程内存: {memory_stats.get('max_process_memory_mb', 0):.1f}MB")
        print(f"内存限制: {memory_stats.get('memory_limit_mb', 0)}MB")
        
        print("="*50)
    
    def cleanup(self):
        """清理资源"""
        try:
            self.performance_monitor.stop_monitoring()
            self.memory_manager.stop_monitoring()
            self.logger.info("资源清理完成")
        except Exception as e:
            self.logger.error(f"资源清理失败: {e}")


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建示例实例
    example = OptimizedWasteDetectionExample()
    
    try:
        # 启动监控
        example.start_monitoring()
        
        # 运行模拟检测
        example.simulate_detection_loop(duration=30)
        
        # 显示性能报告
        example.get_performance_report()
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logging.error(f"程序异常: {e}")
    finally:
        # 清理资源
        example.cleanup()


if __name__ == "__main__":
    main()
