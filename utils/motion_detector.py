#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运动检测器 - 废弃物AI识别指导投放系统
基于OpenCV的基础运动检测实现
"""

import time
import cv2
import numpy as np
import logging
from typing import Optional, Dict, Any, Tuple


class MotionDetector:
    """运动检测器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化运动检测器"""
        self.logger = logging.getLogger(__name__)

        self.motion_threshold = config.get('motion_threshold', 500)
        self.min_contour_area = config.get('min_contour_area', 1000)
        self.history = config.get('history', 500)
        self.dist2_threshold = config.get('dist2_threshold', 400.0)
        self.detect_shadows = config.get('detect_shadows', True)
        self.blur_kernel_size = config.get('blur_kernel_size', 5)
        self.kernel_size = config.get('kernel_size', 3)
        self.detection_cooldown = config.get('detection_cooldown', 3.0)

        background_model = config.get('background_model', 'MOG2').upper()
        self.use_knn = background_model == 'KNN' or config.get('use_knn_subtractor', False)

        self.bg_subtractor = self._create_background_subtractor()
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.kernel_size, self.kernel_size))

        self.last_detection_time = 0.0
        self.last_frame_brightness: Optional[float] = None
        self.brightness_history = []
        self.brightness_change_threshold = 15.0
        self.max_brightness_history = 10

        self.logger.info(
            "运动检测器初始化完成: threshold=%s, min_area=%s, model=%s",
            self.motion_threshold,
            self.min_contour_area,
            'KNN' if self.use_knn else 'MOG2',
        )

    def _create_background_subtractor(self):
        """创建背景减除器"""
        if self.use_knn:
            return cv2.createBackgroundSubtractorKNN(
                history=self.history,
                dist2Threshold=self.dist2_threshold,
                detectShadows=self.detect_shadows,
            )
        return cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.motion_threshold,
            detectShadows=self.detect_shadows,
        )

    def detect_motion(self, frame: np.ndarray) -> bool:
        """检测帧中的运动"""
        try:
            if frame is None:
                return False

            processed_frame, skip_frame = self._preprocess_frame(frame)
            if skip_frame or processed_frame is None:
                return False

            fg_mask = self.bg_subtractor.apply(processed_frame)
            _, binary_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
            cleaned_mask = self._postprocess_mask(binary_mask)
            contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            current_time = time.time()
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > self.min_contour_area:
                    if (current_time - self.last_detection_time) >= self.detection_cooldown:
                        self.last_detection_time = current_time
                        self.logger.debug("检测到运动: 轮廓面积=%.0f", area)
                        return True
                    else:
                        self.logger.debug("运动检测处于冷却期，忽略重复触发")
                        return False
            return False

        except Exception as e:
            self.logger.error("运动检测失败: %s", e)
            return False

    def _preprocess_frame(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """预处理帧，返回(处理后的帧, 是否跳过本帧)"""
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        if self._is_lighting_change(gray):
            self.logger.debug("检测到光照突变，跳过本帧")
            return None, True

        blurred = cv2.GaussianBlur(gray, (self.blur_kernel_size, self.blur_kernel_size), 0)
        return blurred, False

    def _postprocess_mask(self, mask: np.ndarray) -> np.ndarray:
        """后处理掩码"""
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self.kernel)
        return closed

    def _is_lighting_change(self, gray_frame: np.ndarray) -> bool:
        """检测是否为光照变化"""
        try:
            current_brightness = float(np.mean(gray_frame))
            if self.last_frame_brightness is None:
                self.last_frame_brightness = current_brightness
                self.brightness_history.append(current_brightness)
                return False

            brightness_change = abs(current_brightness - self.last_frame_brightness)
            self.brightness_history.append(current_brightness)
            if len(self.brightness_history) > self.max_brightness_history:
                self.brightness_history.pop(0)

            if len(self.brightness_history) >= 3:
                recent_changes = [
                    abs(self.brightness_history[i] - self.brightness_history[i - 1])
                    for i in range(1, len(self.brightness_history))
                ]
                avg_recent_change = float(np.mean(recent_changes[-3:])) if recent_changes else 0.0
                if brightness_change > self.brightness_change_threshold and avg_recent_change > self.brightness_change_threshold * 0.5:
                    self.logger.debug(
                        "检测到光照变化: 当前变化=%.1f, 平均变化=%.1f",
                        brightness_change,
                        avg_recent_change,
                    )
                    self.last_frame_brightness = current_brightness
                    return True

            self.last_frame_brightness = current_brightness
            return False

        except Exception as e:
            self.logger.error("光照变化检测失败: %s", e)
            return False

    def get_motion_mask(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """获取运动掩码（用于调试）"""
        try:
            if frame is None:
                return None
            processed_frame, skip_frame = self._preprocess_frame(frame)
            if skip_frame or processed_frame is None:
                return None
            fg_mask = self.bg_subtractor.apply(processed_frame)
            return self._postprocess_mask(fg_mask)
        except Exception as e:
            self.logger.error("获取运动掩码失败: %s", e)
            return None

    def reset(self):
        """重置背景模型"""
        try:
            self.bg_subtractor = self._create_background_subtractor()
            self.last_detection_time = 0.0
            self.logger.info("运动检测器背景模型已重置")
        except Exception as e:
            self.logger.error("重置运动检测器失败: %s", e)

    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        try:
            reinit = False

            if 'motion_threshold' in config:
                self.motion_threshold = config['motion_threshold']
                if not self.use_knn:
                    reinit = True

            if 'min_contour_area' in config:
                self.min_contour_area = config['min_contour_area']

            if 'history' in config:
                self.history = config['history']
                reinit = True

            if 'dist2_threshold' in config:
                self.dist2_threshold = config['dist2_threshold']
                if self.use_knn:
                    reinit = True

            if 'detect_shadows' in config:
                self.detect_shadows = config['detect_shadows']
                reinit = True

            if 'blur_kernel_size' in config:
                self.blur_kernel_size = config['blur_kernel_size']

            if 'kernel_size' in config:
                self.kernel_size = config['kernel_size']
                self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.kernel_size, self.kernel_size))

            if 'detection_cooldown' in config:
                self.detection_cooldown = config['detection_cooldown']

            if 'background_model' in config or 'use_knn_subtractor' in config:
                background_model = config.get('background_model', 'KNN' if self.use_knn else 'MOG2').upper()
                self.use_knn = background_model == 'KNN' or config.get('use_knn_subtractor', self.use_knn)
                reinit = True

            if reinit:
                self.bg_subtractor = self._create_background_subtractor()

            self.logger.info(
                "运动检测器配置已更新: threshold=%s, min_area=%s, model=%s",
                self.motion_threshold,
                self.min_contour_area,
                'KNN' if self.use_knn else 'MOG2',
            )

        except Exception as e:
            self.logger.error("更新运动检测器配置失败: %s", e)
