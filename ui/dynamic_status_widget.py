#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态状态显示组件 - 废弃物AI识别指导投放系统
替换原有的垃圾分类指导区域，实现识别流程状态动画
"""

import math
import logging
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QFrame, QProgressBar, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal, QParallelAnimationGroup
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen, QMovie

from utils.config_manager import get_config_manager
from utils.voice_guide import get_voice_guide


class AnimatedIcon(QLabel):
    """动画图标组件 - 使用Qt原生动画"""

    def __init__(self, icon_text: str = "🔍", size: int = 80):
        super().__init__()
        self.icon_text = icon_text
        self.size = size
        self.current_opacity = 1.0
        self.opacity_direction = -1

        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Arial", size // 2))

        # 使用透明度变化代替transform动画
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._update_pulse)

        # 旋转动画使用文本切换模拟
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self._update_rotation)
        self.rotation_icons = ["🔄", "🔃", "⟳", "⟲"]
        self.rotation_index = 0

        self._update_display()

    def _update_display(self):
        """更新显示"""
        self.setText(self.icon_text)

        # 使用Qt支持的样式
        # 仅通过 QFont 控制字号，避免 px 固定像素
        self.setStyleSheet(f"""
            QLabel {{
                color: #3498db;
                background: transparent;
            }}
        """)

        # 设置透明度
        self.setWindowOpacity(self.current_opacity)

    def _update_pulse(self):
        """更新脉冲效果（透明度变化）"""
        self.current_opacity += 0.05 * self.opacity_direction
        if self.current_opacity >= 1.0:
            self.current_opacity = 1.0
            self.opacity_direction = -1
        elif self.current_opacity <= 0.3:
            self.current_opacity = 0.3
            self.opacity_direction = 1

        # 使用样式表设置透明度效果
        opacity_value = int(self.current_opacity * 255)
        self.setStyleSheet(f"""
            QLabel {{
                color: rgba(52, 152, 219, {opacity_value});
                background: transparent;
            }}
        """)

    def _update_rotation(self):
        """更新旋转效果（图标切换）"""
        self.rotation_index = (self.rotation_index + 1) % len(self.rotation_icons)
        rotation_icon = self.rotation_icons[self.rotation_index]
        self.setText(rotation_icon)

    def start_rotation(self):
        """开始旋转动画"""
        self.stop_pulse()  # 停止脉冲
        self.rotation_timer.start(200)  # 200ms间隔

    def stop_rotation(self):
        """停止旋转动画"""
        self.rotation_timer.stop()
        self.rotation_index = 0
        self._update_display()

    def start_pulse(self):
        """开始脉冲动画"""
        self.stop_rotation()  # 停止旋转
        self.current_opacity = 1.0
        self.opacity_direction = -1
        self.pulse_timer.start(100)  # 100ms间隔

    def stop_pulse(self):
        """停止脉冲动画"""
        self.pulse_timer.stop()
        self.current_opacity = 1.0
        self._update_display()

    def set_icon(self, icon_text: str):
        """设置图标"""
        self.icon_text = icon_text
        self.stop_rotation()
        self.stop_pulse()
        self._update_display()


class StatusProgressBar(QProgressBar):
    """状态进度条"""
    
    def __init__(self):
        super().__init__()
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(8)
        
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 2px;
            }
        """)
        
        # 进度动画
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.target_value = 0
        self.current_value = 0
    
    def animate_to(self, target: int, duration: int = 1000):
        """动画到目标值"""
        self.target_value = target
        self.progress_timer.start(20)  # 20ms间隔
    
    def _update_progress(self):
        """更新进度"""
        if self.current_value < self.target_value:
            self.current_value += 2
            if self.current_value >= self.target_value:
                self.current_value = self.target_value
                self.progress_timer.stop()
        elif self.current_value > self.target_value:
            self.current_value -= 2
            if self.current_value <= self.target_value:
                self.current_value = self.target_value
                self.progress_timer.stop()
        
        self.setValue(self.current_value)


class DynamicStatusWidget(QFrame):
    """动态状态显示组件"""
    
    # 状态枚举
    STATE_WAITING = "waiting"
    STATE_DETECTED = "detected"
    STATE_RECOGNIZING = "recognizing"
    STATE_SUCCESS = "success"
    STATE_ERROR = "error"
    
    # 信号
    status_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 初始化配置
        self.config_manager = get_config_manager()
        # 避免与主窗口语音系统重复初始化，禁用本组件内置语音
        self.voice_guide = None
        
        # 当前状态
        self.current_state = self.STATE_WAITING
        self.recognition_result = None
        
        # 设置UI
        self._setup_ui()
        self._setup_style()
        
        # 初始状态
        self.set_waiting_state()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题区域
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel("智能识别状态")
        self.title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        
        title_layout.addWidget(self.title_label)
        layout.addLayout(title_layout)
        
        # 主要状态显示区域
        self.status_frame = QFrame()
        self.status_frame.setMinimumHeight(300)
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(30, 30, 30, 30)
        status_layout.setSpacing(25)
        
        # 动画图标
        icon_layout = QHBoxLayout()
        self.animated_icon = AnimatedIcon("🔍", 100)
        icon_layout.addStretch()
        icon_layout.addWidget(self.animated_icon)
        icon_layout.addStretch()
        status_layout.addLayout(icon_layout)
        
        # 状态文本
        self.status_text = QLabel("请将垃圾放入检测区域")
        self.status_text.setFont(QFont("Microsoft YaHei", 16))
        self.status_text.setAlignment(Qt.AlignCenter)
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet("color: #34495e; padding: 15px;")
        status_layout.addWidget(self.status_text)
        
        # 进度条（初始隐藏）
        self.progress_bar = StatusProgressBar()
        self.progress_bar.hide()
        status_layout.addWidget(self.progress_bar)
        
        # 详细信息区域（用于显示识别结果）
        self.detail_frame = QFrame()
        self.detail_frame.hide()
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(20, 20, 20, 20)
        detail_layout.setSpacing(15)
        
        # 识别结果标题
        self.result_title = QLabel()
        self.result_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.result_title.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.result_title)
        
        # 识别结果描述
        self.result_description = QLabel()
        self.result_description.setFont(QFont("Microsoft YaHei", 12))
        self.result_description.setWordWrap(True)
        self.result_description.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.result_description)
        
        # 投放指导
        self.guidance_text = QLabel()
        self.guidance_text.setFont(QFont("Microsoft YaHei", 13, QFont.Bold))
        self.guidance_text.setWordWrap(True)
        self.guidance_text.setAlignment(Qt.AlignCenter)
        detail_layout.addWidget(self.guidance_text)
        
        status_layout.addWidget(self.detail_frame)

        # 最近捕获图片显示区域
        self.captured_image_frame = QFrame()
        self.captured_image_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        self.captured_image_frame.hide()

        captured_image_layout = QVBoxLayout(self.captured_image_frame)
        captured_image_layout.setSpacing(8)

        # 图片标题
        captured_image_title = QLabel("最近捕获的图片")
        captured_image_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        captured_image_title.setAlignment(Qt.AlignCenter)
        captured_image_title.setStyleSheet("color: #495057; padding: 5px;")

        # 图片显示标签
        self.captured_image_label = QLabel()
        self.captured_image_label.setMinimumSize(200, 150)
        self.captured_image_label.setMaximumSize(300, 225)
        self.captured_image_label.setAlignment(Qt.AlignCenter)
        self.captured_image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                color: #6c757d;
            }
        """)
        self.captured_image_label.setText("暂无图片")

        captured_image_layout.addWidget(captured_image_title)
        captured_image_layout.addWidget(self.captured_image_label)

        status_layout.addWidget(self.captured_image_frame)
        status_layout.addStretch()

        layout.addWidget(self.status_frame)
        layout.addStretch()
    
    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            DynamicStatusWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border: 2px solid #dee2e6;
                border-radius: 15px;
            }
        """)
        
        self.status_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid #dee2e6;
                border-radius: 10px;
            }
        """)
        
        self.detail_frame.setStyleSheet("""
            QFrame {
                background: rgba(248, 249, 250, 0.95);
                border: 1px solid #e9ecef;
                border-radius: 8px;
            }
        """)
    
    def set_waiting_state(self, keep_last_result: bool = True):
        """设置等待检测状态"""
        if self.current_state == self.STATE_WAITING:
            return

        self.current_state = self.STATE_WAITING
        self.logger.info("状态切换: 等待检测")

        # 更新UI
        self.animated_icon.set_icon("🔍")
        self.animated_icon.stop_rotation()
        self.animated_icon.start_pulse()

        self.status_text.setText("请将垃圾放入检测区域")
        self.status_text.setStyleSheet("color: #6c757d; padding: 15px;")

        self.progress_bar.hide()

        # 如果要保持上一次结果且有识别结果，则保持显示；否则隐藏
        if not (keep_last_result and self.recognition_result):
            self.detail_frame.hide()

        self.status_changed.emit(self.STATE_WAITING)
    
    def set_detected_state(self):
        """设置检测到物体状态"""
        if self.current_state == self.STATE_DETECTED:
            return
        
        self.current_state = self.STATE_DETECTED
        self.logger.info("状态切换: 检测到物体")
        
        # 更新UI
        self.animated_icon.set_icon("👁️")
        self.animated_icon.stop_pulse()
        self.animated_icon.start_pulse()
        
        self.status_text.setText("检测到物体，请保持稳定")
        self.status_text.setStyleSheet("color: #fd7e14; padding: 15px;")
        
        self.progress_bar.hide()
        self.detail_frame.hide()
        
        self.status_changed.emit(self.STATE_DETECTED)
    
    def set_recognizing_state(self, progress: int = 0):
        """设置正在识别状态"""
        if self.current_state != self.STATE_RECOGNIZING:
            self.current_state = self.STATE_RECOGNIZING
            self.logger.info("状态切换: 正在识别")
            
            # 更新UI
            self.animated_icon.set_icon("🤖")
            self.animated_icon.stop_pulse()
            self.animated_icon.start_rotation()
            
            self.status_text.setText("正在识别中，请稍候...")
            self.status_text.setStyleSheet("color: #0d6efd; padding: 15px;")
            
            self.progress_bar.show()
            self.detail_frame.hide()
            
            self.status_changed.emit(self.STATE_RECOGNIZING)
        
        # 更新进度
        self.progress_bar.animate_to(progress)
    
    def set_success_state(self, result: Dict[str, Any]):
        """设置识别成功状态"""
        self.current_state = self.STATE_SUCCESS
        self.recognition_result = result
        self.logger.info(f"状态切换: 识别成功 - {result.get('category', '未知')}")
        
        # 更新UI
        category = result.get('category', '其他垃圾-其他类-未知物品')
        description = result.get('description', '无描述信息')
        
        # 获取分类信息
        category_info = self._get_category_info(category)
        icon = category_info.get('icon', '✅') if category_info else '✅'
        color = category_info.get('color', '#28a745') if category_info else '#28a745'
        guidance = category_info.get('guidance', '请按照相关规定投放') if category_info else '请按照相关规定投放'
        
        self.animated_icon.set_icon(icon)
        self.animated_icon.stop_rotation()
        self.animated_icon.stop_pulse()
        
        self.status_text.setText(f"识别完成！")
        self.status_text.setStyleSheet("color: #198754; padding: 15px;")
        
        self.progress_bar.hide()
        
        # 解析层级分类格式
        if '-' in category:
            category_parts = category.split('-')
            main_category = category_parts[0] if len(category_parts) > 0 else category
            specific_item = category_parts[2] if len(category_parts) > 2 else category_parts[-1]
            display_title = f"{specific_item} ({main_category})"
        else:
            display_title = category
            main_category = category

        # 显示详细结果
        self.result_title.setText(display_title)
        self.result_title.setStyleSheet(f"color: {color}; padding: 10px;")
        
        self.result_description.setText(description)
        self.result_description.setStyleSheet("color: #495057; padding: 8px;")
        
        self.guidance_text.setText(f"投放指导：{guidance}")
        self.guidance_text.setStyleSheet(f"color: {color}; background-color: rgba(255,255,255,0.8); padding: 12px; border-radius: 6px; border: 1px solid {color};")
        
        self.detail_frame.show()
        
        self.status_changed.emit(self.STATE_SUCCESS)
        
        # 语音由主窗口统一管理，避免与此处重复播放造成并发冲突
    
    def set_error_state(self, error_message: str = "识别失败"):
        """设置错误状态"""
        self.current_state = self.STATE_ERROR
        self.logger.warning(f"状态切换: 错误 - {error_message}")
        
        # 更新UI
        self.animated_icon.set_icon("❌")
        self.animated_icon.stop_rotation()
        self.animated_icon.stop_pulse()
        
        self.status_text.setText(f"识别失败：{error_message}")
        self.status_text.setStyleSheet("color: #dc3545; padding: 15px;")
        
        self.progress_bar.hide()
        self.detail_frame.hide()
        
        self.status_changed.emit(self.STATE_ERROR)
        
        # 3秒后自动返回等待状态，保持上一次的检测结果
        QTimer.singleShot(3000, lambda: self.set_waiting_state(keep_last_result=True))

    def show_captured_image(self, image_path: str):
        """显示捕获的图片"""
        try:
            import os
            from PySide6.QtGui import QPixmap

            if not os.path.exists(image_path):
                self.logger.warning(f"图片文件不存在: {image_path}")
                return

            # 加载图片
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self.logger.warning(f"无法加载图片: {image_path}")
                return

            # 缩放图片以适应显示区域
            scaled_pixmap = pixmap.scaled(
                self.captured_image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # 显示图片
            self.captured_image_label.setPixmap(scaled_pixmap)
            self.captured_image_frame.show()

            self.logger.info(f"已显示捕获的图片: {os.path.basename(image_path)}")

        except Exception as e:
            self.logger.error(f"显示捕获图片失败: {e}")

    def hide_captured_image(self):
        """隐藏捕获的图片"""
        try:
            self.captured_image_frame.hide()
            self.captured_image_label.clear()
            self.captured_image_label.setText("暂无图片")
        except Exception as e:
            self.logger.error(f"隐藏捕获图片失败: {e}")
    
    def _get_category_info(self, category: str) -> Optional[Dict[str, Any]]:
        """获取分类信息"""
        if self.config_manager:
            try:
                return self.config_manager.get_waste_category_info(category)
            except Exception as e:
                self.logger.error(f"获取分类信息失败: {e}")
        return None
    
    def reset_to_waiting(self):
        """重置到等待状态"""
        QTimer.singleShot(100, self.set_waiting_state)
