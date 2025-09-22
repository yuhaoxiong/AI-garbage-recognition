#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IO控制工作器 - 废弃物AI识别指导投放系统
负责监听红外传感器信号，控制检测流程
"""

import time
import threading
import logging
from typing import Optional, Callable
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker, QTimer
from utils.config_manager import get_config_manager

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("警告: RPi.GPIO库未安装，将使用模拟IO")


class IOControlWorker(QThread):
    """IO控制工作器"""
    
    # 信号定义
    ir_signal_detected = Signal()      # 红外信号检测到
    ir_signal_lost = Signal()          # 红外信号丢失
    detection_trigger = Signal(bool)   # 检测触发信号 (True=开始检测, False=停止检测)
    
    def __init__(self):
        """初始化IO控制工作器"""
        super().__init__()
        
        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.io_config = self.config_manager.get_io_config()
        
        # IO配置
        self.ir_pin = self.io_config.ir_sensor_pin
        self.detection_delay = self.io_config.detection_delay
        self.detection_timeout = self.io_config.detection_timeout
        self.debounce_time = self.io_config.debounce_time
        
        # 状态管理
        self.is_running = False
        self.ir_detected = False
        self.last_ir_time = 0
        self.detection_active = False
        self.mutex = QMutex()
        
        # 定时器
        self.detection_timer = QTimer()
        self.detection_timer.setSingleShot(True)
        self.detection_timer.timeout.connect(self._stop_detection)
        
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._process_ir_signal)
        
        # 初始化GPIO
        self._init_gpio()
        
        self.logger.info("IO控制工作器初始化完成")
    
    def _init_gpio(self):
        """初始化GPIO"""
        if not GPIO_AVAILABLE:
            self.logger.warning("GPIO不可用，将使用模拟IO")
            return
        
        try:
            # 设置GPIO模式
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 设置红外传感器引脚
            GPIO.setup(self.ir_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # 设置中断回调
            GPIO.add_event_detect(self.ir_pin, GPIO.BOTH, 
                                callback=self._ir_interrupt_callback, 
                                bouncetime=int(self.debounce_time * 1000))
            
            self.logger.info(f"GPIO初始化成功，红外传感器引脚: {self.ir_pin}")
            
        except Exception as e:
            self.logger.error(f"GPIO初始化失败: {e}")
    
    def _ir_interrupt_callback(self, channel):
        """红外传感器中断回调"""
        current_time = time.time()
        
        with QMutexLocker(self.mutex):
            self.last_ir_time = current_time
            
            # 启动防抖定时器
            self.debounce_timer.start(int(self.debounce_time * 1000))
    
    def _process_ir_signal(self):
        """处理红外信号"""
        if not GPIO_AVAILABLE:
            return
        
        try:
            # 读取当前状态
            current_state = GPIO.input(self.ir_pin) == GPIO.LOW  # 低电平表示检测到物体
            
            with QMutexLocker(self.mutex):
                if current_state != self.ir_detected:
                    self.ir_detected = current_state
                    
                    if self.ir_detected:
                        self.logger.info("红外信号检测到")
                        self.ir_signal_detected.emit()
                        self._start_detection()
                    else:
                        self.logger.info("红外信号丢失")
                        self.ir_signal_lost.emit()
                        # 不立即停止检测，等待超时
                        
        except Exception as e:
            self.logger.error(f"处理红外信号失败: {e}")
    
    def _start_detection(self):
        """开始检测"""
        with QMutexLocker(self.mutex):
            if not self.detection_active:
                self.detection_active = True
                self.logger.info("开始AI检测")
                
                # 延迟启动检测（给用户时间放置物品）
                QTimer.singleShot(int(self.detection_delay * 1000), 
                                self._trigger_detection)
                
                # 设置检测超时
                self.detection_timer.start(int(self.detection_timeout * 1000))
    
    def _trigger_detection(self):
        """触发检测"""
        with QMutexLocker(self.mutex):
            if self.detection_active:
                self.detection_trigger.emit(True)
    
    def _stop_detection(self):
        """停止检测"""
        with QMutexLocker(self.mutex):
            if self.detection_active:
                self.detection_active = False
                self.logger.info("停止AI检测")
                self.detection_trigger.emit(False)
                self.detection_timer.stop()
    
    def run(self):
        """主运行循环"""
        self.is_running = True
        self.logger.info("IO控制工作器开始运行")
        
        # 模拟IO模式
        if not GPIO_AVAILABLE:
            self._simulate_io_mode()
            return
        
        # 实际GPIO模式
        while self.is_running:
            try:
                # 检查是否需要停止检测（红外信号丢失超时）
                current_time = time.time()
                with QMutexLocker(self.mutex):
                    if (self.detection_active and 
                        not self.ir_detected and 
                        current_time - self.last_ir_time > self.detection_timeout):
                        self._stop_detection()
                
                # 短暂休眠
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"IO控制运行错误: {e}")
                time.sleep(1)
        
        self.logger.info("IO控制工作器停止运行")
    
    def _simulate_io_mode(self):
        """模拟IO模式（用于测试）"""
        self.logger.info("启动模拟IO模式")
        
        # 模拟定期触发检测
        while self.is_running:
            try:
                # 模拟检测到红外信号
                if not self.detection_active:
                    self.logger.info("模拟：红外信号检测到")
                    self.ir_signal_detected.emit()
                    self._start_detection()
                
                # 等待一段时间
                time.sleep(8)
                
                # 模拟信号丢失
                if self.detection_active:
                    self.logger.info("模拟：红外信号丢失")
                    self.ir_signal_lost.emit()
                    self._stop_detection()
                
                # 等待下一次循环
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"模拟IO模式错误: {e}")
                time.sleep(1)
    
    def stop(self):
        """停止工作器"""
        self.is_running = False
        self._stop_detection()
        
        # 清理GPIO
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
                self.logger.info("GPIO清理完成")
            except:
                pass
        
        self.quit()
        self.wait()
    
    def get_status(self) -> dict:
        """获取IO状态"""
        with QMutexLocker(self.mutex):
            return {
                'ir_detected': self.ir_detected,
                'detection_active': self.detection_active,
                'last_ir_time': self.last_ir_time,
                'gpio_available': GPIO_AVAILABLE
            }
    
    def force_trigger(self):
        """强制触发检测（用于测试）"""
        self.logger.info("强制触发检测")
        self.ir_signal_detected.emit()
        self._start_detection()
    
    def manual_stop(self):
        """手动停止检测"""
        self.logger.info("手动停止检测")
        self._stop_detection() 