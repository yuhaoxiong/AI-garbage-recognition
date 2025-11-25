#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IO控制工作器 - 废弃物AI识别指导投放系统
负责监听红外传感器信号，控制检测流程
"""

import time
import logging
from typing import Optional
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker
from utils.config_manager import get_config_manager

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("警告: RPi.GPIO库未安装，将使用模拟IO")


class IOControlWorker(QThread):
    """IO控制工作器"""

    ir_signal_detected = Signal()      # 红外信号检测到
    ir_signal_lost = Signal()          # 红外信号丢失
    detection_trigger = Signal(bool)   # 检测触发信号(True=开始检测, False=停止检测)

    def __init__(self):
        super().__init__()

        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)

        self.io_config = self.config_manager.get_io_config()
        self.ir_pin = self.io_config.ir_sensor_pin
        self.detection_delay = self.io_config.detection_delay
        self.detection_timeout = self.io_config.detection_timeout
        self.debounce_time = self.io_config.debounce_time

        self.is_running = False
        self.ir_detected = False
        self.last_ir_time = 0.0
        self.detection_active = False
        self.mutex = QMutex()

        self._debounce_pending = False
        self._detection_trigger_time: Optional[float] = None
        self._pending_trigger_sent = False

        self._init_gpio()
        self.logger.info("IO控制工作器初始化完成")

    def _init_gpio(self):
        if not GPIO_AVAILABLE:
            self.logger.warning("GPIO不可用，将使用模拟IO")
            return

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.ir_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                self.ir_pin,
                GPIO.BOTH,
                callback=self._ir_interrupt_callback,
                bouncetime=int(self.debounce_time * 1000)
            )
            self.logger.info(f"GPIO初始化成功，红外传感器引脚: {self.ir_pin}")
        except Exception as e:
            self.logger.error(f"GPIO初始化失败: {e}")

    def _ir_interrupt_callback(self, channel):
        current_time = time.time()
        with QMutexLocker(self.mutex):
            self.last_ir_time = current_time
            self._debounce_pending = True

    def _start_detection(self):
        should_log = False
        with QMutexLocker(self.mutex):
            if not self.detection_active:
                self.detection_active = True
                self._pending_trigger_sent = False
                self._detection_trigger_time = time.time() + max(self.detection_delay, 0.0)
                should_log = True
        if should_log:
            self.logger.info("开始AI检测")

    def _trigger_detection(self):
        emit = False
        with QMutexLocker(self.mutex):
            if self.detection_active and not self._pending_trigger_sent:
                self._pending_trigger_sent = True
                emit = True
        if emit:
            self.detection_trigger.emit(True)

    def _stop_detection(self):
        emit = False
        with QMutexLocker(self.mutex):
            if self.detection_active:
                self.detection_active = False
                self._pending_trigger_sent = False
                self._detection_trigger_time = None
                emit = True
        if emit:
            self.logger.info("停止AI检测")
            self.detection_trigger.emit(False)

    def run(self):
        self.is_running = True
        self.logger.info("IO控制工作器开始运行")

        if not GPIO_AVAILABLE:
            self._simulate_io_mode()
            return

        while self.is_running:
            actions = []
            current_time = time.time()
            with QMutexLocker(self.mutex):
                if self._debounce_pending and (current_time - self.last_ir_time) >= self.debounce_time:
                    self._debounce_pending = False
                    try:
                        current_state = GPIO.input(self.ir_pin) == GPIO.LOW
                    except Exception as e:
                        self.logger.error(f"读取红外传感器状态失败: {e}")
                        current_state = None
                    if current_state is not None and current_state != self.ir_detected:
                        self.ir_detected = current_state
                        if self.ir_detected:
                            actions.append('ir_detected')
                        else:
                            self.last_ir_time = current_time
                            actions.append('ir_lost')

                trigger_due = False
                stop_due = False
                if self.detection_active:
                    if (self._detection_trigger_time is not None
                            and current_time >= self._detection_trigger_time
                            and not self._pending_trigger_sent):
                        trigger_due = True
                    if (not self.ir_detected
                            and current_time - self.last_ir_time > self.detection_timeout):
                        stop_due = True

                if trigger_due:
                    actions.append('trigger_detection')
                if stop_due:
                    self.detection_active = False
                    self._pending_trigger_sent = False
                    self._detection_trigger_time = None
                    actions.append('stop_detection')

            for action in actions:
                if action == 'ir_detected':
                    self.logger.info("红外信号检测到")
                    self.ir_signal_detected.emit()
                    self._start_detection()
                elif action == 'ir_lost':
                    self.logger.info("红外信号丢失")
                    self.ir_signal_lost.emit()
                elif action == 'trigger_detection':
                    self._trigger_detection()
                elif action == 'stop_detection':
                    self._stop_detection()

            time.sleep(0.05)

        self.logger.info("IO控制工作器停止运行")

    def _simulate_io_mode(self):
        self.logger.info("启动模拟IO模式")
        while self.is_running:
            try:
                if not self.detection_active:
                    with QMutexLocker(self.mutex):
                        self.ir_detected = True
                        self.last_ir_time = time.time()
                    self.logger.info("模拟：红外信号检测到")
                    self.ir_signal_detected.emit()
                    self._start_detection()

                time.sleep(8)

                with QMutexLocker(self.mutex):
                    self.ir_detected = False
                    self.last_ir_time = time.time()
                self.logger.info("模拟：红外信号丢失")
                self.ir_signal_lost.emit()
                self._stop_detection()

                time.sleep(5)

            except Exception as e:
                self.logger.error(f"模拟IO模式错误: {e}")
                time.sleep(1)

    def stop(self):
        self.is_running = False
        self._stop_detection()

        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
                self.logger.info("GPIO清理完成")
            except Exception:
                pass

        self.quit()
        self.wait()

    def get_status(self) -> dict:
        with QMutexLocker(self.mutex):
            return {
                'ir_detected': self.ir_detected,
                'detection_active': self.detection_active,
                'last_ir_time': self.last_ir_time,
                'gpio_available': GPIO_AVAILABLE
            }

    def force_trigger(self):
        self.logger.info("强制触发检测")
        self.ir_signal_detected.emit()
        self._start_detection()

    def manual_stop(self):
        self.logger.info("手动停止检测")
        self._stop_detection()
