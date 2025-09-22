#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画播放组件 - 废弃物AI识别指导投放系统
负责播放各种动画效果，提升用户体验
"""

import os
import math
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                           QRect, QPoint, QSize, Signal, QParallelAnimationGroup,
                           QSequentialAnimationGroup)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen, QMovie

from worker.waste_detection_worker import WasteDetectionResult
from utils.config_manager import get_config_manager


class ParticleEffect(QWidget):
    """粒子效果组件"""
    
    def __init__(self, parent=None):
        """初始化粒子效果"""
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 粒子参数
        self.particles = []
        self.particle_count = 20
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_particles)
        
        # 动画状态
        self.is_animating = False
        self.animation_color = QColor(46, 204, 113)  # 默认绿色
        
    def start_animation(self, color: QColor = None):
        """开始粒子动画"""
        if color:
            self.animation_color = color
        
        self.is_animating = True
        self.particles = []
        
        # 创建粒子
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        for i in range(self.particle_count):
            angle = (2 * math.pi * i) / self.particle_count
            velocity_x = math.cos(angle) * 2
            velocity_y = math.sin(angle) * 2
            
            particle = {
                'x': center_x,
                'y': center_y,
                'vx': velocity_x,
                'vy': velocity_y,
                'life': 1.0,
                'size': 3 + (i % 3)
            }
            self.particles.append(particle)
        
        self.animation_timer.start(50)  # 20 FPS
        
        # 3秒后停止动画
        QTimer.singleShot(3000, self.stop_animation)
    
    def stop_animation(self):
        """停止粒子动画"""
        self.is_animating = False
        self.animation_timer.stop()
        self.particles = []
        self.update()
    
    def update_particles(self):
        """更新粒子状态"""
        if not self.is_animating:
            return
        
        # 更新粒子位置和生命周期
        for particle in self.particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.02
            
            # 应用重力
            particle['vy'] += 0.1
        
        # 移除生命周期结束的粒子
        self.particles = [p for p in self.particles if p['life'] > 0]
        
        # 如果所有粒子都消失，停止动画
        if not self.particles:
            self.stop_animation()
        
        self.update()
    
    def paintEvent(self, event):
        """绘制粒子"""
        if not self.is_animating:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for particle in self.particles:
            # 计算透明度
            alpha = int(255 * particle['life'])
            color = QColor(self.animation_color)
            color.setAlpha(alpha)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # 绘制粒子
            painter.drawEllipse(
                int(particle['x']), int(particle['y']),
                particle['size'], particle['size']
            )


class SuccessAnimation(QWidget):
    """成功动画组件"""
    
    def __init__(self, parent=None):
        """初始化成功动画"""
        super().__init__(parent)
        self.setFixedSize(100, 100)
        
        # 动画组件
        self.check_label = QLabel("✓", self)
        self.check_label.setAlignment(Qt.AlignCenter)
        self.check_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.check_label.setStyleSheet("color: #27ae60;")
        self.check_label.setGeometry(0, 0, 100, 100)
        
        # 初始状态
        self.check_label.setVisible(False)
        
        # 动画效果
        self.opacity_effect = QGraphicsOpacityEffect()
        self.check_label.setGraphicsEffect(self.opacity_effect)
        
        # 动画对象
        self.scale_animation = QPropertyAnimation(self.check_label, b"geometry")
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        
        # 创建动画组
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.scale_animation)
        self.animation_group.addAnimation(self.opacity_animation)
        
    def start_animation(self):
        """开始成功动画"""
        self.check_label.setVisible(True)
        
        # 设置初始状态
        self.check_label.setGeometry(40, 40, 20, 20)
        self.opacity_effect.setOpacity(0)
        
        # 配置缩放动画
        self.scale_animation.setDuration(800)
        self.scale_animation.setStartValue(QRect(40, 40, 20, 20))
        self.scale_animation.setEndValue(QRect(0, 0, 100, 100))
        self.scale_animation.setEasingCurve(QEasingCurve.OutBack)
        
        # 配置透明度动画
        self.opacity_animation.setDuration(800)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutQuart)
        
        # 开始动画
        self.animation_group.start()
        
        # 2秒后隐藏
        QTimer.singleShot(2000, self.hide_animation)
    
    def hide_animation(self):
        """隐藏动画"""
        self.check_label.setVisible(False)


class PulseAnimation(QWidget):
    """脉冲动画组件"""
    
    def __init__(self, parent=None):
        """初始化脉冲动画"""
        super().__init__(parent)
        self.setFixedSize(150, 150)
        
        # 动画状态
        self.is_animating = False
        self.pulse_radius = 0
        self.pulse_color = QColor(52, 152, 219)
        
        # 动画定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_pulse)
        
    def start_animation(self, color: QColor = None):
        """开始脉冲动画"""
        if color:
            self.pulse_color = color
        
        self.is_animating = True
        self.pulse_radius = 0
        self.animation_timer.start(50)  # 20 FPS
        
        # 3秒后停止
        QTimer.singleShot(3000, self.stop_animation)
    
    def stop_animation(self):
        """停止脉冲动画"""
        self.is_animating = False
        self.animation_timer.stop()
        self.update()
    
    def update_pulse(self):
        """更新脉冲效果"""
        if not self.is_animating:
            return
        
        self.pulse_radius += 3
        if self.pulse_radius > 75:
            self.pulse_radius = 0
        
        self.update()
    
    def paintEvent(self, event):
        """绘制脉冲效果"""
        if not self.is_animating:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        # 绘制多个脉冲圆环
        for i in range(3):
            radius = self.pulse_radius - i * 25
            if radius > 0:
                alpha = int(255 * (1 - radius / 75))
                color = QColor(self.pulse_color)
                color.setAlpha(alpha)
                
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    center_x - radius, center_y - radius,
                    radius * 2, radius * 2
                )


class AnimationWidget(QWidget):
    """动画播放主组件"""
    
    # 信号定义
    animation_finished = Signal(str)  # 动画完成信号
    
    def __init__(self, parent=None):
        """初始化动画组件"""
        super().__init__(parent)
        
        self.config_manager = get_config_manager()
        self.animation_config = self.config_manager.get_animation_config()
        
        self._setup_ui()
        self._setup_animations()
        
    def _setup_ui(self):
        """设置UI"""
        self.setFixedSize(300, 300)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        
        # 动画容器
        self.animation_container = QFrame()
        self.animation_container.setFixedSize(250, 250)
        self.animation_container.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 125px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
        """)
        
        layout.addWidget(self.animation_container)
        
        # 状态标签
        self.status_label = QLabel("等待检测...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.status_label.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        
        layout.addWidget(self.status_label)
        
    def _setup_animations(self):
        """设置动画组件"""
        # 创建各种动画效果
        self.particle_effect = ParticleEffect(self.animation_container)
        self.particle_effect.move(25, 25)
        
        self.success_animation = SuccessAnimation(self.animation_container)
        self.success_animation.move(75, 75)
        
        self.pulse_animation = PulseAnimation(self.animation_container)
        self.pulse_animation.move(50, 50)
        
        # 隐藏所有动画
        self.particle_effect.hide()
        self.success_animation.hide()
        self.pulse_animation.hide()
    
    def play_detection_animation(self):
        """播放检测动画"""
        self.status_label.setText("正在检测...")
        self.status_label.setStyleSheet("color: #3498db; margin-top: 10px;")
        
        # 显示脉冲动画
        self.pulse_animation.show()
        self.pulse_animation.start_animation(QColor(52, 152, 219))
    
    def play_success_animation(self, results: List[WasteDetectionResult]):
        """播放成功识别动画"""
        if not results:
            return
        
        # 停止检测动画
        self.pulse_animation.stop_animation()
        self.pulse_animation.hide()
        
        # 更新状态
        if len(results) == 1:
            self.status_label.setText(f"识别成功: {results[0].waste_category}")
        else:
            self.status_label.setText(f"识别成功: {len(results)}个物品")
        
        self.status_label.setStyleSheet("color: #27ae60; margin-top: 10px;")
        
        # 获取第一个结果的颜色
        first_result = results[0]
        color = QColor(first_result.color)
        
        # 播放成功动画
        self.success_animation.show()
        self.success_animation.start_animation()
        
        # 播放粒子效果
        self.particle_effect.show()
        self.particle_effect.start_animation(color)
        
        # 3秒后隐藏动画
        QTimer.singleShot(3000, self._hide_all_animations)
        
        # 发送完成信号
        QTimer.singleShot(3000, lambda: self.animation_finished.emit("success"))
    
    def play_waiting_animation(self):
        """播放等待动画"""
        self.status_label.setText("请放置物品...")
        self.status_label.setStyleSheet("color: #f39c12; margin-top: 10px;")
        
        # 显示轻微的脉冲动画
        self.pulse_animation.show()
        self.pulse_animation.start_animation(QColor(243, 156, 18))
    
    def play_error_animation(self, error_message: str):
        """播放错误动画"""
        self.status_label.setText(f"错误: {error_message}")
        self.status_label.setStyleSheet("color: #e74c3c; margin-top: 10px;")
        
        # 停止其他动画
        self._hide_all_animations()
        
        # 播放错误脉冲
        self.pulse_animation.show()
        self.pulse_animation.start_animation(QColor(231, 76, 60))
        
        # 3秒后恢复等待状态
        QTimer.singleShot(3000, self.reset_animation)
    
    def reset_animation(self):
        """重置动画状态"""
        self._hide_all_animations()
        self.status_label.setText("等待检测...")
        self.status_label.setStyleSheet("color: #7f8c8d; margin-top: 10px;")
        
        # 发送重置信号
        self.animation_finished.emit("reset")
    
    def _hide_all_animations(self):
        """隐藏所有动画"""
        self.particle_effect.stop_animation()
        self.particle_effect.hide()
        
        self.success_animation.hide_animation()
        self.success_animation.hide()
        
        self.pulse_animation.stop_animation()
        self.pulse_animation.hide()
    
    def set_animation_enabled(self, enabled: bool):
        """设置动画开关"""
        self.setVisible(enabled)
        if not enabled:
            self._hide_all_animations()
    
    def get_animation_status(self) -> str:
        """获取当前动画状态"""
        if self.particle_effect.is_animating:
            return "success"
        elif self.pulse_animation.is_animating:
            return "detecting"
        else:
            return "idle" 