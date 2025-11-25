#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能运动检测器 - 针对垃圾投放场景优化
专门面向人员将垃圾移动至摄像头范围内的场景设计
"""

import cv2
import numpy as np
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass


class MotionState(Enum):
    """运动状态枚举"""
    NO_MOTION = "no_motion"           # 无运动
    ENTERING = "entering"             # 物体进入
    PRESENT_MOVING = "present_moving" # 物体存在且移动
    PRESENT_STABLE = "present_stable" # 物体存在且稳定
    LEAVING = "leaving"               # 物体离开


@dataclass
class MotionEvent:
    """运动事件"""
    state: MotionState
    timestamp: float
    contour_area: float
    center_point: Tuple[int, int]
    stability_duration: float = 0.0


class SmartMotionDetector:
    """智能运动检测器 - 垃圾投放场景优化"""

    def __init__(self, config: Dict[str, Any]):
        """初始化智能运动检测器"""
        self.logger = logging.getLogger(__name__)

        # 基础配置
        self.motion_threshold = config.get('motion_threshold', 800)
        self.min_contour_area = config.get('min_contour_area', 1500)
        self.history = config.get('history', 500)
        self.detect_shadows = config.get('detect_shadows', True)

        # 垃圾投放场景专用配置
        self.roi_enabled = config.get('roi_enabled', True)
        self.roi_top_ratio = config.get('roi_top_ratio', 0.2)
        self.roi_bottom_ratio = config.get('roi_bottom_ratio', 0.8)
        self.roi_left_ratio = config.get('roi_left_ratio', 0.1)
        self.roi_right_ratio = config.get('roi_right_ratio', 0.9)

        # 稳定性配置
        self.stability_threshold = config.get('stability_threshold', 50)
        self.min_stability_duration = config.get('min_stability_duration', 1.0)
        self.max_stability_duration = config.get('max_stability_duration', 5.0)

        # 误触发过滤配置
        self.min_presence_area = config.get('min_presence_area', 3000)
        self.center_movement_threshold = config.get('center_movement_threshold', 100)
        self.min_presence_duration = config.get('min_presence_duration', 0.5)
        self.background_change_threshold = config.get('background_change_threshold', 0.1)
        self.detection_cooldown = config.get('detection_cooldown', 3.0)

        # 背景建模
        self.bg_subtractor = self._create_background_subtractor()
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # 状态跟踪
        self.current_state = MotionState.NO_MOTION
        self.last_center: Optional[Tuple[int, int]] = None
        self.last_area: float = 0.0
        self.state_start_time = time.time()
        self.stability_start_time: Optional[float] = None
        self.motion_history: List[Dict[str, Any]] = []
        self.frame_size: Optional[Tuple[int, int]] = None
        self.roi_rect: Optional[Tuple[int, int, int, int]] = None
        self.last_stable_event_time: float = 0.0
        self.last_event_area: float = 0.0

        # 光照变化监控
        self.last_frame_brightness: Optional[float] = None
        self.brightness_history: List[float] = []
        self.brightness_change_threshold = 15.0
        self.max_brightness_history = 10

        self.logger.info("智能运动检测器初始化完成 - 垃圾投放场景优化")
        self.logger.info(
            "配置: threshold=%s, min_area=%s, ROI=%s",
            self.motion_threshold,
            self.min_contour_area,
            self.roi_enabled,
        )

    def _create_background_subtractor(self):
        """创建背景减除器"""
        return cv2.createBackgroundSubtractorMOG2(
            history=self.history,
            varThreshold=self.motion_threshold,
            detectShadows=self.detect_shadows
        )

    def detect_motion_smart(self, frame: np.ndarray) -> Optional[MotionEvent]:
        """智能运动检测 - 返回运动事件"""
        try:
            if frame is None:
                return None

            if self.frame_size is None:
                self._init_frame_info(frame)

            processed_frame, skip_frame = self._preprocess_frame(frame)
            if skip_frame or processed_frame is None:
                return None

            if self.roi_enabled:
                processed_frame = self._apply_roi(processed_frame)

            fg_mask = self.bg_subtractor.apply(processed_frame)
            cleaned_mask = self._postprocess_mask(fg_mask)

            motion_info = self._analyze_motion(cleaned_mask)
            if motion_info.get('background_change'):
                self.logger.debug(
                    "检测到大范围背景波动，active_ratio=%.2f，跳过当前帧",
                    motion_info['active_ratio']
                )
                return None

            motion_event = self._process_state_machine(motion_info)
            self._update_history(motion_info)
            return motion_event

        except Exception as e:
            self.logger.warning("智能运动检测处理异常: %s", e)
            return None

    def _init_frame_info(self, frame: np.ndarray):
        """初始化帧信息"""
        self.frame_size = (frame.shape[1], frame.shape[0])
        if self.roi_enabled:
            w, h = self.frame_size
            x1 = int(w * self.roi_left_ratio)
            y1 = int(h * self.roi_top_ratio)
            x2 = int(w * self.roi_right_ratio)
            y2 = int(h * self.roi_bottom_ratio)
            self.roi_rect = (x1, y1, x2 - x1, y2 - y1)
            self.logger.info("ROI区域设置: %s", self.roi_rect)

    def _apply_roi(self, frame: np.ndarray) -> np.ndarray:
        """应用感兴趣区域"""
        if not self.roi_enabled or self.roi_rect is None:
            return frame
        x, y, w, h = self.roi_rect
        roi_frame = np.zeros_like(frame)
        roi_frame[y:y + h, x:x + w] = frame[y:y + h, x:x + w]
        return roi_frame

    def _analyze_motion(self, mask: np.ndarray) -> Dict[str, Any]:
        """分析运动信息"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_pixels = mask.size if mask is not None else 0
        active_pixels = int(cv2.countNonZero(mask)) if total_pixels else 0
        active_ratio = active_pixels / total_pixels if total_pixels else 0.0

        if not contours:
            return {
                'has_motion': False,
                'total_area': 0.0,
                'largest_area': 0.0,
                'largest_contour': None,
                'center': None,
                'contour_count': 0,
                'active_ratio': active_ratio,
                'background_change': active_ratio > self.background_change_threshold,
            }

        largest_contour = max(contours, key=cv2.contourArea)
        largest_area = cv2.contourArea(largest_contour)
        total_area = sum(cv2.contourArea(c) for c in contours)

        center = None
        if largest_area > 0:
            m = cv2.moments(largest_contour)
            if m.get("m00"):
                cx = int(m["m10"] / m["m00"])
                cy = int(m["m01"] / m["m00"])
                center = (cx, cy)

        background_change = False
        if active_ratio > self.background_change_threshold and largest_area < self.min_presence_area:
            background_change = True

        return {
            'has_motion': largest_area > self.min_contour_area,
            'total_area': total_area,
            'largest_area': largest_area,
            'largest_contour': largest_contour,
            'center': center,
            'contour_count': len(contours),
            'active_ratio': active_ratio,
            'background_change': background_change,
        }

    def _process_state_machine(self, motion_info: Dict[str, Any]) -> Optional[MotionEvent]:
        """运动状态机"""
        current_time = time.time()
        has_motion = motion_info['has_motion']
        area = motion_info['largest_area']
        center = motion_info['center']
        state_duration = current_time - self.state_start_time
        area_change = abs(area - self.last_area) if self.last_area else 0.0

        center_movement = 0.0
        if self.last_center and center:
            center_movement = np.hypot(center[0] - self.last_center[0], center[1] - self.last_center[1])

        new_state = self.current_state
        motion_event: Optional[MotionEvent] = None

        if self.current_state == MotionState.NO_MOTION:
            if has_motion and area > self.min_presence_area:
                new_state = MotionState.ENTERING
                self.logger.info("检测到物体进入: 面积=%.0f", area)

        elif self.current_state == MotionState.ENTERING:
            if not has_motion:
                new_state = MotionState.NO_MOTION
            elif area > self.min_presence_area and state_duration >= self.min_presence_duration:
                if center_movement < self.center_movement_threshold and area_change <= self.stability_threshold:
                    new_state = MotionState.PRESENT_STABLE
                    self.stability_start_time = current_time
                    self.logger.info("物体开始稳定: 中心移动=%.1f", center_movement)
                else:
                    new_state = MotionState.PRESENT_MOVING

        elif self.current_state == MotionState.PRESENT_MOVING:
            if not has_motion:
                new_state = MotionState.LEAVING
            elif center_movement < self.center_movement_threshold and area_change <= self.stability_threshold:
                new_state = MotionState.PRESENT_STABLE
                self.stability_start_time = current_time
                self.logger.info("物体从移动转为稳定")

        elif self.current_state == MotionState.PRESENT_STABLE:
            if not has_motion:
                new_state = MotionState.LEAVING
            elif center_movement > self.center_movement_threshold or area_change > self.stability_threshold:
                new_state = MotionState.PRESENT_MOVING
                self.stability_start_time = None
                self.logger.info("物体从稳定转为移动")
            else:
                if self.stability_start_time:
                    stability_duration = current_time - self.stability_start_time
                    if self.min_stability_duration <= stability_duration <= self.max_stability_duration:
                        if (current_time - self.last_stable_event_time) >= self.detection_cooldown:
                            motion_event = MotionEvent(
                                state=MotionState.PRESENT_STABLE,
                                timestamp=current_time,
                                contour_area=area,
                                center_point=center if center else (0, 0),
                                stability_duration=stability_duration,
                            )
                            self.last_stable_event_time = current_time
                            self.last_event_area = area
                            self.logger.info("物体稳定采集条件满足: 稳定时间=%.1fs", stability_duration)
                        else:
                            self.logger.debug("稳定状态仍在冷却期，跳过事件触发")

        elif self.current_state == MotionState.LEAVING:
            if has_motion and area > self.min_presence_area:
                new_state = MotionState.PRESENT_MOVING
            else:
                if state_duration > 0.5:
                    new_state = MotionState.NO_MOTION
                    self.logger.info("确认物体离开")

        if new_state != self.current_state:
            self.current_state = new_state
            self.state_start_time = current_time
            if new_state != MotionState.PRESENT_STABLE:
                self.stability_start_time = None
                self.last_event_area = 0.0

        self.last_center = center
        self.last_area = area
        return motion_event

    def _update_history(self, motion_info: Dict[str, Any]):
        """更新运动历史"""
        snapshot = {
            'timestamp': time.time(),
            'has_motion': motion_info['has_motion'],
            'area': motion_info['largest_area'],
            'state': self.current_state,
            'active_ratio': motion_info.get('active_ratio', 0.0),
        }
        self.motion_history.append(snapshot)
        if len(self.motion_history) > 100:
            self.motion_history = self.motion_history[-50:]

    def _preprocess_frame(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], bool]:
        """预处理帧，返回(处理后的帧, 是否跳过本帧)"""
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        if self._is_lighting_change(gray):
            self.logger.debug("检测到光照突变，跳过本帧运动分析")
            return None, True

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
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

    def get_roi_visualization(self, frame: np.ndarray) -> np.ndarray:
        """获取ROI可视化图像"""
        if not self.roi_enabled or self.roi_rect is None:
            return frame
        vis_frame = frame.copy()
        x, y, w, h = self.roi_rect
        cv2.rectangle(vis_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(vis_frame, "Waste Drop Zone", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return vis_frame

    def get_current_state_info(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        current_time = time.time()
        state_duration = current_time - self.state_start_time
        stability_duration = 0.0
        if self.stability_start_time:
            stability_duration = current_time - self.stability_start_time
        return {
            'state': self.current_state.value,
            'state_duration': state_duration,
            'stability_duration': stability_duration,
            'last_center': self.last_center,
            'last_area': self.last_area,
            'roi_rect': self.roi_rect,
        }

    def get_motion_mask(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """获取运动掩码用于调试"""
        try:
            if frame is None:
                return None
            processed_frame, skip_frame = self._preprocess_frame(frame)
            if skip_frame or processed_frame is None:
                return None
            if self.roi_enabled:
                processed_frame = self._apply_roi(processed_frame)
            fg_mask = self.bg_subtractor.apply(processed_frame)
            return self._postprocess_mask(fg_mask)
        except Exception as e:
            self.logger.error("获取运动掩码失败: %s", e)
            return None

    def reset(self):
        """重置检测器状态"""
        self.bg_subtractor = self._create_background_subtractor()
        self.current_state = MotionState.NO_MOTION
        self.last_center = None
        self.last_area = 0.0
        self.state_start_time = time.time()
        self.stability_start_time = None
        self.motion_history.clear()
        self.last_stable_event_time = 0.0
        self.last_event_area = 0.0
        self.logger.info("智能运动检测器已重置")

    def detect_motion(self, frame: np.ndarray) -> bool:
        """兼容原有接口的布尔返回"""
        return self.detect_motion_smart(frame) is not None
