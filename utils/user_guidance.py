#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户指导模块 - 垃圾投放场景用户体验优化
提供视觉和声音提示，指导用户正确投放垃圾
"""

import cv2
import numpy as np
import logging
import time
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from utils.smart_motion_detector import MotionState


class GuidanceState(Enum):
    """指导状态枚举"""
    WAITING = "waiting"           # 等待投放
    DETECTED = "detected"         # 检测到物体
    POSITIONING = "positioning"   # 物体定位中
    STABLE = "stable"            # 物体稳定
    CAPTURING = "capturing"       # 正在采集
    PROCESSING = "processing"     # 正在识别
    COMPLETED = "completed"       # 完成识别
    ERROR = "error"              # 错误状态


class UserGuidance:
    """用户指导系统"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化用户指导系统
        
        Args:
            config: 配置字典
        """
        self.logger = logging.getLogger(__name__)
        
        # 配置参数
        self.enable_visual_guidance = config.get('enable_visual_guidance', True)
        self.enable_voice_guidance = config.get('enable_voice_guidance', True)
        self.guidance_language = config.get('guidance_language', 'zh')
        
        # 视觉指导配置
        self.show_roi = config.get('show_roi', True)
        self.show_status_text = config.get('show_status_text', True)
        self.show_progress_bar = config.get('show_progress_bar', True)
        
        # 颜色配置
        self.colors = {
            'roi_normal': (0, 255, 0),      # 绿色 - 正常ROI
            'roi_active': (0, 255, 255),    # 黄色 - 活跃ROI
            'roi_stable': (255, 0, 255),    # 紫色 - 稳定ROI
            'text_normal': (255, 255, 255), # 白色 - 正常文本
            'text_warning': (0, 255, 255),  # 黄色 - 警告文本
            'text_success': (0, 255, 0),    # 绿色 - 成功文本
            'text_error': (0, 0, 255),      # 红色 - 错误文本
        }
        
        # 状态跟踪
        self.current_guidance_state = GuidanceState.WAITING
        self.last_guidance_time = 0
        self.guidance_messages = self._init_guidance_messages()
        
        # 进度跟踪
        self.stability_progress = 0.0
        self.processing_progress = 0.0
        
        self.logger.info("用户指导系统初始化完成")
    
    def _init_guidance_messages(self) -> Dict[str, Dict[str, str]]:
        """初始化指导消息"""
        return {
            'zh': {
                GuidanceState.WAITING.value: "请将垃圾放入绿色区域",
                GuidanceState.DETECTED.value: "检测到物体，请保持稳定",
                GuidanceState.POSITIONING.value: "正在定位，请稍等...",
                GuidanceState.STABLE.value: "物体稳定，准备拍照",
                GuidanceState.CAPTURING.value: "正在拍照，请保持不动",
                GuidanceState.PROCESSING.value: "正在识别，请稍候...",
                GuidanceState.COMPLETED.value: "识别完成！",
                GuidanceState.ERROR.value: "出现错误，请重试"
            },
            'en': {
                GuidanceState.WAITING.value: "Please place waste in green area",
                GuidanceState.DETECTED.value: "Object detected, keep stable",
                GuidanceState.POSITIONING.value: "Positioning, please wait...",
                GuidanceState.STABLE.value: "Object stable, ready to capture",
                GuidanceState.CAPTURING.value: "Capturing, stay still",
                GuidanceState.PROCESSING.value: "Processing, please wait...",
                GuidanceState.COMPLETED.value: "Recognition completed!",
                GuidanceState.ERROR.value: "Error occurred, please retry"
            }
        }
    
    def update_motion_state(self, motion_state: MotionState, motion_info: Optional[Dict[str, Any]] = None):
        """
        根据运动状态更新指导状态
        
        Args:
            motion_state: 运动状态
            motion_info: 运动信息
        """
        # 状态映射
        state_mapping = {
            MotionState.NO_MOTION: GuidanceState.WAITING,
            MotionState.ENTERING: GuidanceState.DETECTED,
            MotionState.PRESENT_MOVING: GuidanceState.POSITIONING,
            MotionState.PRESENT_STABLE: GuidanceState.STABLE,
            MotionState.LEAVING: GuidanceState.WAITING
        }
        
        new_state = state_mapping.get(motion_state, GuidanceState.WAITING)
        
        if new_state != self.current_guidance_state:
            self.current_guidance_state = new_state
            self.last_guidance_time = time.time()
            self.logger.debug(f"指导状态更新: {new_state.value}")
        
        # 更新稳定性进度
        if motion_info and 'stability_duration' in motion_info:
            max_duration = motion_info.get('max_stability_duration', 3.0)
            self.stability_progress = min(motion_info['stability_duration'] / max_duration, 1.0)
    
    def update_processing_state(self, state: str, progress: float = 0.0):
        """
        更新处理状态
        
        Args:
            state: 处理状态 ('capturing', 'processing', 'completed', 'error')
            progress: 进度 (0.0-1.0)
        """
        state_mapping = {
            'capturing': GuidanceState.CAPTURING,
            'processing': GuidanceState.PROCESSING,
            'completed': GuidanceState.COMPLETED,
            'error': GuidanceState.ERROR
        }
        
        new_state = state_mapping.get(state, self.current_guidance_state)
        
        if new_state != self.current_guidance_state:
            self.current_guidance_state = new_state
            self.last_guidance_time = time.time()
        
        self.processing_progress = progress
    
    def draw_guidance_overlay(self, frame: np.ndarray, roi_rect: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        绘制指导覆盖层
        
        Args:
            frame: 输入帧
            roi_rect: ROI矩形 (x, y, w, h)
            
        Returns:
            带指导覆盖层的帧
        """
        if not self.enable_visual_guidance:
            return frame
        
        overlay_frame = frame.copy()
        
        # 绘制ROI区域
        if self.show_roi and roi_rect:
            self._draw_roi(overlay_frame, roi_rect)
        
        # 绘制状态文本
        if self.show_status_text:
            self._draw_status_text(overlay_frame)
        
        # 绘制进度条
        if self.show_progress_bar:
            self._draw_progress_bar(overlay_frame)
        
        return overlay_frame
    
    def _draw_roi(self, frame: np.ndarray, roi_rect: Tuple[int, int, int, int]):
        """绘制ROI区域"""
        x, y, w, h = roi_rect
        
        # 选择颜色
        if self.current_guidance_state == GuidanceState.WAITING:
            color = self.colors['roi_normal']
            thickness = 2
        elif self.current_guidance_state in [GuidanceState.DETECTED, GuidanceState.POSITIONING]:
            color = self.colors['roi_active']
            thickness = 3
        elif self.current_guidance_state == GuidanceState.STABLE:
            color = self.colors['roi_stable']
            thickness = 4
        else:
            color = self.colors['roi_normal']
            thickness = 2
        
        # 绘制矩形
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        
        # 绘制角落标记
        corner_length = 30
        corner_thickness = 4
        
        # 左上角
        cv2.line(frame, (x, y), (x + corner_length, y), color, corner_thickness)
        cv2.line(frame, (x, y), (x, y + corner_length), color, corner_thickness)
        
        # 右上角
        cv2.line(frame, (x + w, y), (x + w - corner_length, y), color, corner_thickness)
        cv2.line(frame, (x + w, y), (x + w, y + corner_length), color, corner_thickness)
        
        # 左下角
        cv2.line(frame, (x, y + h), (x + corner_length, y + h), color, corner_thickness)
        cv2.line(frame, (x, y + h), (x, y + h - corner_length), color, corner_thickness)
        
        # 右下角
        cv2.line(frame, (x + w, y + h), (x + w - corner_length, y + h), color, corner_thickness)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_length), color, corner_thickness)
        
        # 绘制区域标签
        label = "投放区域"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        label_x = x + (w - label_size[0]) // 2
        label_y = y - 10
        
        cv2.putText(frame, label, (label_x, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    def _draw_status_text(self, frame: np.ndarray):
        """绘制状态文本"""
        # 获取状态消息
        messages = self.guidance_messages.get(self.guidance_language, self.guidance_messages['zh'])
        message = messages.get(self.current_guidance_state.value, "")
        
        if not message:
            return
        
        # 选择文本颜色
        if self.current_guidance_state == GuidanceState.ERROR:
            color = self.colors['text_error']
        elif self.current_guidance_state == GuidanceState.COMPLETED:
            color = self.colors['text_success']
        elif self.current_guidance_state in [GuidanceState.DETECTED, GuidanceState.POSITIONING]:
            color = self.colors['text_warning']
        else:
            color = self.colors['text_normal']
        
        # 绘制背景
        text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = 50
        
        # 半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (text_x - 20, text_y - 35), 
                     (text_x + text_size[0] + 20, text_y + 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # 绘制文本
        cv2.putText(frame, message, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    
    def _draw_progress_bar(self, frame: np.ndarray):
        """绘制进度条"""
        if self.current_guidance_state not in [GuidanceState.STABLE, GuidanceState.PROCESSING]:
            return
        
        # 进度条参数
        bar_width = 300
        bar_height = 20
        bar_x = (frame.shape[1] - bar_width) // 2
        bar_y = frame.shape[0] - 80
        
        # 选择进度值
        if self.current_guidance_state == GuidanceState.STABLE:
            progress = self.stability_progress
            label = "稳定性"
            color = self.colors['roi_stable']
        else:  # PROCESSING
            progress = self.processing_progress
            label = "识别进度"
            color = self.colors['text_warning']
        
        # 绘制进度条背景
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (50, 50, 50), -1)
        
        # 绘制进度
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), 
                         color, -1)
        
        # 绘制边框
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), 
                     (255, 255, 255), 2)
        
        # 绘制标签和百分比
        label_text = f"{label}: {int(progress * 100)}%"
        cv2.putText(frame, label_text, (bar_x, bar_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    def get_voice_guidance(self) -> Optional[str]:
        """
        获取语音指导内容
        
        Returns:
            语音指导文本，如果不需要语音则返回None
        """
        if not self.enable_voice_guidance:
            return None
        
        # 避免频繁语音提示
        current_time = time.time()
        if current_time - self.last_guidance_time < 3.0:  # 3秒内不重复提示
            return None
        
        messages = self.guidance_messages.get(self.guidance_language, self.guidance_messages['zh'])
        return messages.get(self.current_guidance_state.value, None)
    
    def reset(self):
        """重置指导状态"""
        self.current_guidance_state = GuidanceState.WAITING
        self.last_guidance_time = 0
        self.stability_progress = 0.0
        self.processing_progress = 0.0
        
        self.logger.debug("用户指导系统已重置")
