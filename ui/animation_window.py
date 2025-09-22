#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立动画窗口 - 废弃物AI识别指导投放系统
显示gif动画和粒子特效的独立窗口
"""

import os
import math
import logging
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect,
                              QPushButton, QCheckBox, QSlider, QSpinBox, QGroupBox)
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                           QRect, QPoint, QSize, Signal, QParallelAnimationGroup,
                           QSequentialAnimationGroup, QThread)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen, QMovie

from worker.waste_detection_worker import WasteDetectionResult
from utils.config_manager import get_config_manager


class GifDisplayWidget(QWidget):
    """Gif动画显示组件"""
    
    def __init__(self, parent=None):
        """初始化gif显示组件"""
        super().__init__(parent)
        self.setFixedSize(400, 400)
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Gif显示标签
        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
            }
        """)
        
        layout.addWidget(self.gif_label)
        
        # 当前播放的gif
        self.current_movie = None
        self.gif_paths = self._load_gif_paths()
        
        # 默认显示
        self.show_default_image()
    
    def _load_gif_paths(self) -> Dict[str, str]:
        """加载gif文件路径映射"""
        # 获取当前脚本的目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 从配置中获取gif目录，如果没有则使用默认值
        config_manager = get_config_manager()
        animation_config = config_manager.get_animation_config()
        gif_dir = animation_config.gif_directory
        
        # 构建绝对路径
        gif_dir_path = os.path.join(script_dir, gif_dir)
        
        # 确保目录存在
        if not os.path.exists(gif_dir_path):
            os.makedirs(gif_dir_path, exist_ok=True)
            logging.warning(f"gif目录不存在，已创建: {gif_dir_path}")
        
        logging.info(f"gif目录路径: {gif_dir_path}")
        
        # 默认gif文件映射
        gif_mapping = {
            "可回收物": os.path.join(gif_dir_path, "recyclable.gif"),
            "有害垃圾": os.path.join(gif_dir_path, "hazardous.gif"),
            "湿垃圾": os.path.join(gif_dir_path, "wet.gif"),
            "干垃圾": os.path.join(gif_dir_path, "dry.gif"),
            "默认": os.path.join(gif_dir_path, "default.gif")
        }
        
        # 记录所有映射路径
        for category, path in gif_mapping.items():
            exists = os.path.exists(path)
            logging.info(f"gif映射: {category} -> {path} (存在: {exists})")
        
        return gif_mapping
    
    def show_default_image(self):
        """显示默认图片"""
        # 停止当前动画
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None
        
        # 清除movie设置
        self.gif_label.setMovie(None)
        
        # 显示默认文本
        self.gif_label.setText("等待识别结果...")
        self.gif_label.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 10px;
                color: #7f8c8d;
                font-size: 16px;
            }
        """)
    
    def show_category_gif(self, category: str):
        """显示分类对应的gif"""
        gif_path = self.gif_paths.get(category, self.gif_paths.get("默认"))
        
        logging.info(f"尝试显示gif: {category}, 路径: {gif_path}")
        
        if gif_path and os.path.exists(gif_path):
            # 检查文件大小
            try:
                file_size = os.path.getsize(gif_path)
                logging.info(f"gif文件大小: {file_size} bytes")
                
                # 检查文件是否可读
                with open(gif_path, 'rb') as f:
                    header = f.read(6)
                    logging.info(f"文件头: {header}")
                    
                    # 检查GIF文件头
                    if header[:3] == b'GIF':
                        logging.info("文件头验证成功，这是一个GIF文件")
                        self._play_gif(gif_path)
                    else:
                        logging.error(f"文件头验证失败，不是有效的GIF文件: {header}")
                        self._show_text_fallback(f"{category} - 文件格式错误")
                        
            except Exception as e:
                logging.error(f"检查gif文件时出错: {e}")
                self._show_text_fallback(f"{category} - 文件检查失败")
        else:
            logging.warning(f"gif文件不存在: {gif_path}")
            self._show_text_fallback(category)
    
    def _play_gif(self, gif_path: str):
        """播放gif动画"""
        try:
            logging.info(f"开始播放gif: {gif_path}")
            
            # 停止当前动画
            if self.current_movie:
                logging.info("停止当前动画")
                self.current_movie.stop()
            
            # 创建新的QMovie
            self.current_movie = QMovie(gif_path)
            
            # 检查QMovie是否有效
            if not self.current_movie.isValid():
                logging.error(f"QMovie无效: {gif_path}")
                self._show_text_fallback("gif格式错误")
                return
            
            logging.info(f"QMovie创建成功，帧数: {self.current_movie.frameCount()}")
            
            # 设置到标签
            self.gif_label.setMovie(self.current_movie)
            
            # 获取标签尺寸
            label_size = self.gif_label.size()
            logging.info(f"标签尺寸: {label_size}")
            
            # 设置缩放尺寸为标签尺寸
            if label_size.width() > 0 and label_size.height() > 0:
                # 使用标签的实际尺寸
                scaled_size = label_size
            else:
                # 使用固定尺寸
                scaled_size = QSize(400, 400)
            
            logging.info(f"设置缩放尺寸: {scaled_size}")
            self.current_movie.setScaledSize(scaled_size)
            
            # 开始播放
            self.current_movie.start()
            
            # 检查播放状态
            if self.current_movie.state() == QMovie.Running:
                logging.info("gif开始播放")
                # 清除标签文本，确保gif能够显示
                self.gif_label.setText("")
            else:
                logging.error(f"gif播放失败，状态: {self.current_movie.state()}")
                self._show_text_fallback("播放失败")
            
        except Exception as e:
            logging.error(f"播放gif失败: {e}")
            import traceback
            logging.error(f"详细错误: {traceback.format_exc()}")
            self._show_text_fallback("播放失败")
    
    def _show_text_fallback(self, text: str):
        """显示文本替代方案"""
        # 停止当前动画
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None
        
        # 清除movie设置
        self.gif_label.setMovie(None)
        
        # 显示文本
        self.gif_label.setText(text)
        self.gif_label.setStyleSheet("""
            QLabel {
                background-color: rgba(52, 152, 219, 0.2);
                border: 2px solid #3498db;
                border-radius: 10px;
                color: #2c3e50;
                font-size: 18px;
                font-weight: bold;
            }
        """)
    
    def stop_animation(self):
        """停止动画"""
        if self.current_movie:
            self.current_movie.stop()
            self.current_movie = None
        self.show_default_image()


class ParticleEffectWidget(QWidget):
    """粒子效果组件"""
    
    def __init__(self, parent=None):
        """初始化粒子效果"""
        super().__init__(parent)
        self.setFixedSize(400, 400)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # 粒子参数
        self.particles = []
        self.particle_count = 30
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_particles)
        
        # 动画状态
        self.is_animating = False
        self.animation_color = QColor(46, 204, 113)
        
        # 控制参数
        self.gravity = 0.1
        self.particle_size_range = (2, 6)
        self.velocity_range = (1, 4)
        
    def start_animation(self, color: QColor = None, particle_count: int = None):
        """开始粒子动画"""
        if color:
            self.animation_color = color
        
        if particle_count:
            self.particle_count = particle_count
        
        self.is_animating = True
        self.particles = []
        
        # 创建粒子
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        for i in range(self.particle_count):
            angle = (2 * math.pi * i) / self.particle_count
            velocity_magnitude = self.velocity_range[0] + (self.velocity_range[1] - self.velocity_range[0]) * (i % 3) / 3
            velocity_x = math.cos(angle) * velocity_magnitude
            velocity_y = math.sin(angle) * velocity_magnitude
            
            particle = {
                'x': center_x + (i % 20 - 10) * 2,  # 稍微分散起始位置
                'y': center_y + (i % 20 - 10) * 2,
                'vx': velocity_x,
                'vy': velocity_y,
                'life': 1.0,
                'size': self.particle_size_range[0] + (i % (self.particle_size_range[1] - self.particle_size_range[0] + 1)),
                'trail': []  # 粒子轨迹
            }
            self.particles.append(particle)
        
        self.animation_timer.start(50)  # 20 FPS
        
        # 5秒后停止动画
        QTimer.singleShot(5000, self.stop_animation)
    
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
        
        for particle in self.particles:
            # 保存轨迹
            particle['trail'].append((particle['x'], particle['y']))
            if len(particle['trail']) > 5:  # 保持轨迹长度
                particle['trail'].pop(0)
            
            # 更新位置
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.015
            
            # 应用重力
            particle['vy'] += self.gravity
            
            # 边界反弹
            if particle['x'] < 0 or particle['x'] > self.width():
                particle['vx'] *= -0.8
            if particle['y'] < 0 or particle['y'] > self.height():
                particle['vy'] *= -0.8
        
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
            # 绘制粒子轨迹
            if len(particle['trail']) > 1:
                for i in range(1, len(particle['trail'])):
                    alpha = int(100 * particle['life'] * (i / len(particle['trail'])))
                    trail_color = QColor(self.animation_color)
                    trail_color.setAlpha(alpha)
                    
                    painter.setPen(QPen(trail_color, 1))
                    painter.drawLine(
                        int(particle['trail'][i-1][0]), int(particle['trail'][i-1][1]),
                        int(particle['trail'][i][0]), int(particle['trail'][i][1])
                    )
            
            # 绘制粒子
            alpha = int(255 * particle['life'])
            color = QColor(self.animation_color)
            color.setAlpha(alpha)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            
            # 绘制圆形粒子
            painter.drawEllipse(
                int(particle['x'] - particle['size']/2), 
                int(particle['y'] - particle['size']/2),
                particle['size'], particle['size']
            )
    
    def set_particle_count(self, count: int):
        """设置粒子数量"""
        self.particle_count = count
    
    def set_gravity(self, gravity: float):
        """设置重力"""
        self.gravity = gravity


class AnimationWindow(QWidget):
    """独立动画窗口"""
    
    # 信号定义
    window_closed = Signal()
    
    def __init__(self, parent=None):
        """初始化动画窗口"""
        super().__init__(parent)
        
        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._setup_connections()
        
        # 动画状态
        self.current_category = None
        self.is_showing = False
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("垃圾分类动画显示")
        self.setFixedSize(900, 700)
        
        # 设置窗口属性
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("垃圾分类动画显示")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # 动画显示区域
        animation_layout = QHBoxLayout()
        
        # 左侧：gif显示
        gif_group = QGroupBox("Gif动画")
        gif_group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        gif_layout = QVBoxLayout(gif_group)
        
        self.gif_widget = GifDisplayWidget()
        gif_layout.addWidget(self.gif_widget)
        
        animation_layout.addWidget(gif_group)
        
        # 右侧：粒子效果
        particle_group = QGroupBox("粒子特效")
        particle_group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        particle_layout = QVBoxLayout(particle_group)
        
        self.particle_widget = ParticleEffectWidget()
        particle_layout.addWidget(self.particle_widget)
        
        animation_layout.addWidget(particle_group)
        
        main_layout.addLayout(animation_layout)
        
        # 控制面板
        control_group = QGroupBox("控制面板")
        control_group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        control_layout = QVBoxLayout(control_group)
        
        # 第一行控制
        control_row1 = QHBoxLayout()
        
        # 手动测试按钮
        self.test_recyclable_btn = QPushButton("测试可回收物")
        self.test_recyclable_btn.clicked.connect(lambda: self.show_category_animation("可回收物"))
        control_row1.addWidget(self.test_recyclable_btn)
        
        self.test_hazardous_btn = QPushButton("测试有害垃圾")
        self.test_hazardous_btn.clicked.connect(lambda: self.show_category_animation("有害垃圾"))
        control_row1.addWidget(self.test_hazardous_btn)
        
        self.test_wet_btn = QPushButton("测试湿垃圾")
        self.test_wet_btn.clicked.connect(lambda: self.show_category_animation("湿垃圾"))
        control_row1.addWidget(self.test_wet_btn)
        
        self.test_dry_btn = QPushButton("测试干垃圾")
        self.test_dry_btn.clicked.connect(lambda: self.show_category_animation("干垃圾"))
        control_row1.addWidget(self.test_dry_btn)
        
        control_layout.addLayout(control_row1)
        
        # 第二行控制
        control_row2 = QHBoxLayout()
        
        # 粒子数量控制
        control_row2.addWidget(QLabel("粒子数量:"))
        self.particle_count_slider = QSlider(Qt.Horizontal)
        self.particle_count_slider.setRange(10, 100)
        self.particle_count_slider.setValue(30)
        self.particle_count_slider.valueChanged.connect(self._on_particle_count_changed)
        control_row2.addWidget(self.particle_count_slider)
        
        self.particle_count_label = QLabel("30")
        control_row2.addWidget(self.particle_count_label)
        
        # 重力控制
        control_row2.addWidget(QLabel("重力:"))
        self.gravity_slider = QSlider(Qt.Horizontal)
        self.gravity_slider.setRange(0, 50)
        self.gravity_slider.setValue(10)
        self.gravity_slider.valueChanged.connect(self._on_gravity_changed)
        control_row2.addWidget(self.gravity_slider)
        
        self.gravity_label = QLabel("0.1")
        control_row2.addWidget(self.gravity_label)
        
        control_layout.addLayout(control_row2)
        
        # 第三行控制
        control_row3 = QHBoxLayout()
        
        # 重置按钮
        self.reset_btn = QPushButton("重置动画")
        self.reset_btn.clicked.connect(self.reset_animation)
        control_row3.addWidget(self.reset_btn)
        
        # 置顶显示
        self.always_on_top_cb = QCheckBox("窗口置顶")
        self.always_on_top_cb.toggled.connect(self._on_always_on_top_changed)
        control_row3.addWidget(self.always_on_top_cb)
        
        control_row3.addStretch()
        
        control_layout.addLayout(control_row3)
        
        main_layout.addWidget(control_group)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 10px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007bff;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #007bff;
            }
        """)
    
    def _setup_connections(self):
        """设置信号连接"""
        pass
    
    def show_category_animation(self, category: str):
        """显示分类动画"""
        self.current_category = category
        self.is_showing = True
        
        # 显示gif
        self.gif_widget.show_category_gif(category)
        
        # 获取分类颜色
        waste_categories = self.config_manager.get_waste_categories()
        category_info = waste_categories.get(category, {})
        color_hex = category_info.get('color', '#3498db')
        
        # 转换颜色
        color = QColor(color_hex)
        
        # 显示粒子效果
        self.particle_widget.start_animation(color)
        
        # 显示窗口
        if not self.isVisible():
            self.show()
        
        # 置顶显示
        self.raise_()
        self.activateWindow()
        
        self.logger.info(f"显示分类动画: {category}")
    
    def reset_animation(self):
        """重置动画"""
        self.current_category = None
        self.is_showing = False
        
        # 停止所有动画
        self.gif_widget.stop_animation()
        self.particle_widget.stop_animation()
        
        self.logger.info("动画已重置")
    
    def _on_particle_count_changed(self, value: int):
        """粒子数量变化"""
        self.particle_count_label.setText(str(value))
        self.particle_widget.set_particle_count(value)
    
    def _on_gravity_changed(self, value: int):
        """重力变化"""
        gravity = value / 100.0
        self.gravity_label.setText(f"{gravity:.2f}")
        self.particle_widget.set_gravity(gravity)
    
    def _on_always_on_top_changed(self, checked: bool):
        """置顶显示切换"""
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.reset_animation()
        self.window_closed.emit()
        event.accept()
    
    def get_animation_status(self) -> Dict:
        """获取动画状态"""
        return {
            'current_category': self.current_category,
            'is_showing': self.is_showing,
            'gif_playing': self.gif_widget.current_movie is not None,
            'particles_active': self.particle_widget.is_animating
        } 