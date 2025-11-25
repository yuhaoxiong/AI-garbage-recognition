#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
运动检测工作线程 - 废弃物AI识别指导投放系统
负责基于运动检测触发拍照与大模型识别。
'''

import os
import time
import logging
from collections import deque
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from dataclasses import asdict

from utils.config_manager import get_config_manager, MotionDetectionConfig
from utils.smart_motion_detector import SmartMotionDetector, MotionEvent
from utils.motion_detector import MotionDetector as BasicMotionDetector
from utils.api_client import APIClient


class MotionDetectionWorker(QThread):
    '''运动检测工作线程'''

    motion_detected = Signal()  # 触发运动检测事件
    image_captured = Signal(str)  # 捕获图片完成
    api_result_received = Signal(dict)  # 收到API返回
    detection_completed = Signal(dict)  # 完成一次检测流程
    error_occurred = Signal(str)  # 运行异常
    motion_state_changed = Signal(dict)  # 状态机变化

    def __init__(self, camera_worker=None):
        super().__init__()
        self.camera_worker = camera_worker
        self.config_manager = get_config_manager()

        # 读取配置
        self.motion_config: MotionDetectionConfig = self.config_manager.get_motion_detection_config()
        self.api_config = self.config_manager.get_api_config()

        # 检测器选择
        self.use_smart_detector = bool(getattr(self.motion_config, 'use_smart_detector', False))
        self.motion_detector = self._create_motion_detector()

        # API 客户端
        self.api_client = APIClient(asdict(self.api_config))

        # 工作状态
        self.is_running = False
        self.is_enabled = False
        self.mutex = QMutex()

        # 捕获与冷却控制
        self.capture_delay = getattr(self.motion_config, 'capture_delay', 0.0)
        self.max_saved_images = getattr(self.motion_config, 'max_saved_images', 10)
        self._saved_images: deque[str] = deque()
        self._basic_state = 'no_motion'
        self._basic_state_started_at = time.time()
        self._basic_stable_started_at: Optional[float] = None

        # 图片目录
        self.image_dir = 'data/captured_images'
        os.makedirs(self.image_dir, exist_ok=True)

        logging.info(
            '运动检测工作线程初始化完成: smart=%s, capture_delay=%.2fs',
            self.use_smart_detector,
            self.capture_delay,
        )

    def enable_detection(self, enabled: bool):
        '''启用或禁用检测'''
        with QMutexLocker(self.mutex):
            self.is_enabled = enabled
        logging.info('运动检测已%s', '启用' if enabled else '禁用')

    def reset_background(self):
        '''重置背景模型'''
        try:
            if hasattr(self.motion_detector, 'reset'):
                self.motion_detector.reset()
                logging.info('运动检测器背景模型已重置')
        except Exception as exc:
            logging.error('重置运动检测器失败: %s', exc)
            self.error_occurred.emit(f'重置运动检测器失败: {exc}')

    def stop(self):
        '''停止线程'''
        self.is_running = False
        self.requestInterruption()
        if not self.wait(5000):
            logging.warning('运动检测工作线程停止超时，已请求中断')
        else:
            logging.info('运动检测工作线程已停止')

    def run(self):
        self.is_running = True
        logging.info('运动检测工作线程开始运行')

        try:
            while self.is_running:
                if not self._is_detection_enabled():
                    time.sleep(0.1)
                    continue

                frame = self._get_latest_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                detection_output, state_info = self._detect_motion(frame)

                if state_info:
                    self.motion_state_changed.emit(state_info)

                if self.use_smart_detector:
                    if isinstance(detection_output, MotionEvent):
                        self._handle_detection(frame, detection_output, state_info)
                else:
                    if detection_output:
                        self._handle_detection(frame, None, state_info)

                time.sleep(0.05)

        except Exception as exc:
            logging.error('运动检测线程异常: %s', exc)
            self.error_occurred.emit(str(exc))
        finally:
            self.is_running = False
            logging.info('运动检测工作线程退出')

    # ---------------------------
    # 检测与状态辅助
    # ---------------------------
    def _create_motion_detector(self):
        cfg_dict = asdict(self.motion_config)
        if self.use_smart_detector:
            return SmartMotionDetector(cfg_dict)
        return BasicMotionDetector(cfg_dict)

    def _is_detection_enabled(self) -> bool:
        with QMutexLocker(self.mutex):
            return self.is_enabled

    def _get_latest_frame(self) -> Optional[np.ndarray]:
        if self.camera_worker and hasattr(self.camera_worker, 'get_current_frame'):
            try:
                frame = self.camera_worker.get_current_frame()
                if frame is not None:
                    return frame
            except Exception as exc:
                logging.error('获取摄像头帧失败: %s', exc)
        return None

    def _detect_motion(
        self,
        frame: np.ndarray,
    ) -> Tuple[Union[Optional[MotionEvent], bool], Optional[Dict[str, Any]]]:
        if self.use_smart_detector:
            event = self.motion_detector.detect_motion_smart(frame)
            state_info = self.motion_detector.get_current_state_info()
            return event, state_info

        detected = self.motion_detector.detect_motion(frame)
        state_info = self._build_basic_state_info(detected)
        return detected, state_info

    def _build_basic_state_info(self, detected: bool) -> Dict[str, Any]:
        current_time = time.time()
        new_state = 'present_stable' if detected else 'no_motion'

        if new_state != self._basic_state:
            self._basic_state = new_state
            self._basic_state_started_at = current_time
            self._basic_stable_started_at = current_time if detected else None

        state_duration = current_time - self._basic_state_started_at
        stability_duration = 0.0
        if detected and self._basic_stable_started_at:
            stability_duration = current_time - self._basic_stable_started_at

        return {
            'state': new_state,
            'state_duration': state_duration,
            'stability_duration': stability_duration,
            'last_center': None,
            'last_area': 0.0,
            'roi_rect': None,
        }

    # ---------------------------
    # 触发后的处理流程
    # ---------------------------
    def _handle_detection(
        self,
        frame: np.ndarray,
        motion_event: Optional[MotionEvent],
        state_info: Optional[Dict[str, Any]],
    ):
        self.motion_detected.emit()

        if self.capture_delay > 0:
            if not self._wait_with_abort(self.capture_delay):
                return
            refreshed = self._get_latest_frame()
            if refreshed is not None:
                frame = refreshed

        image_path = self._capture_image(frame)
        if not image_path:
            return

        self.image_captured.emit(image_path)
        self._call_api_for_recognition(image_path, motion_event, state_info)

    def _wait_with_abort(self, duration: float) -> bool:
        end_time = time.time() + duration
        while time.time() < end_time:
            if not self.is_running or not self._is_detection_enabled():
                return False
            time.sleep(0.05)
        return True

    def _capture_image(self, frame: np.ndarray) -> Optional[str]:
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f'motion_detected_{timestamp}.jpg'
            image_path = os.path.join(self.image_dir, filename)

            if not cv2.imwrite(image_path, frame):
                raise IOError('写入图像失败')

            self._saved_images.append(image_path)
            self._trim_saved_images()

            logging.info('运动检测已保存图片: %s', image_path)
            return image_path
        except Exception as exc:
            logging.error('图片保存失败: %s', exc)
            self.error_occurred.emit(f'图片保存失败: {exc}')
            return None

    def _trim_saved_images(self):
        if self.max_saved_images <= 0:
            return
        while len(self._saved_images) > self.max_saved_images:
            old_path = self._saved_images.popleft()
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
                    logging.debug('已清理历史图片: %s', old_path)
            except Exception as exc:
                logging.warning('删除历史图片失败: %s', exc)

    def _call_api_for_recognition(
        self,
        image_path: str,
        motion_event: Optional[MotionEvent],
        state_info: Optional[Dict[str, Any]],
    ):
        try:
            if self.isInterruptionRequested():
                return
            logging.info('开始调用大模型API识别...')
            result = self.api_client.call_api(image_path)
            if self.isInterruptionRequested():
                return

            if not result:
                self.error_occurred.emit('API识别失败')
                return

            enriched = dict(result)
            enriched['detection_method'] = 'motion_detection'
            enriched['trigger_time'] = datetime.now().isoformat()

            if motion_event:
                enriched['motion_state'] = motion_event.state.value
                enriched['stability_duration'] = motion_event.stability_duration
            elif state_info:
                enriched['motion_state'] = state_info.get('state')
                enriched['stability_duration'] = state_info.get('stability_duration', 0.0)

            self.api_result_received.emit(enriched)
            self.detection_completed.emit(enriched)
            logging.info('运动检测识别完成: %s', enriched.get('category', '未知'))
        except Exception as exc:
            logging.error('API识别异常: %s', exc)
            self.error_occurred.emit(f'API识别异常: {exc}')
