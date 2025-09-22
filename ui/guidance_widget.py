#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
垃圾投放指导界面 - 废弃物AI识别指导投放系统
显示识别结果和投放指导信息
"""

import os
from typing import List, Optional, Dict, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QFrame, QScrollArea, QGridLayout,
                              QProgressBar, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen

from worker.waste_detection_worker import WasteDetectionResult
from utils.config_manager import get_config_manager
from utils.voice_guide import get_voice_guide


class CategoryCard(QFrame):
    """垃圾分类卡片"""
    
    def __init__(self, category: str, category_info: dict):
        """
        初始化分类卡片
        
        Args:
            category: 分类名称
            category_info: 分类信息
        """
        super().__init__()
        self.category = category
        self.category_info = category_info
        
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # 图标和标题
        header_layout = QHBoxLayout()
        
        # 分类图标 - 改为响应式尺寸
        icon_label = QLabel(self.category_info.get('icon', '🗑️'))
        # 使用相对字体大小，而非固定像素
        icon_label.setFont(QFont("Arial", 24))  # 减小字体大小
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setMinimumSize(40, 40)  # 减小最小尺寸
        icon_label.setMaximumSize(80, 80)  # 设置最大尺寸限制
        
        # 分类名称 - 使用响应式字体
        title_label = QLabel(self.category)
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))  # 减小字体
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)  # 允许换行
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 描述 - 优化字体大小
        desc_label = QLabel(self.category_info.get('description', ''))
        desc_label.setFont(QFont("Microsoft YaHei", 9))  # 减小字体
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignLeft)
        
        # 投放指导 - 优化字体大小和样式
        guidance_label = QLabel(self.category_info.get('guidance', ''))
        guidance_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))  # 减小字体
        guidance_label.setWordWrap(True)
        guidance_label.setAlignment(Qt.AlignLeft)
        guidance_label.setStyleSheet("color: #2c3e50; background-color: rgba(255,255,255,0.8); padding: 8px; border-radius: 5px;")
        
        layout.addLayout(header_layout)
        layout.addWidget(desc_label)
        layout.addWidget(guidance_label)
        layout.addStretch()
        
        # 设置卡片的最小尺寸
        self.setMinimumSize(160, 120)  # 设置更小的最小尺寸
    
    def _setup_style(self):
        """设置样式"""
        color = self.category_info.get('color', '#808080')
        
        self.setStyleSheet(f"""
            CategoryCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}20, stop:1 {color}10);
                border: 2px solid {color};
                border-radius: 15px;
                margin: 5px;
            }}
            CategoryCard:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}40, stop:1 {color}20);
                border: 3px solid {color};
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
    
    def highlight(self):
        """高亮显示"""
        color = self.category_info.get('color', '#808080')
        self.setStyleSheet(f"""
            CategoryCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}80, stop:1 {color}60);
                border: 4px solid {color};
                border-radius: 15px;
                margin: 5px;
            }}
        """)
    
    def reset_style(self):
        """重置样式"""
        self._setup_style()


class DetectionResultWidget(QFrame):
    """检测结果显示组件"""
    
    def __init__(self):
        """初始化检测结果组件"""
        super().__init__()
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("检测结果")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 结果内容区域
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(10)
        
        self.content_area.setWidget(self.content_widget)
        
        # 无检测结果提示
        self.no_result_label = QLabel("暂无检测结果\n请将废弃物放在摄像头前")
        self.no_result_label.setFont(QFont("Microsoft YaHei", 12))
        self.no_result_label.setAlignment(Qt.AlignCenter)
        self.no_result_label.setStyleSheet("color: #7f8c8d; padding: 20px;")
        
        layout.addWidget(title_label)
        layout.addWidget(self.content_area)
        layout.addWidget(self.no_result_label)
    
    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            DetectionResultWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border: 2px solid #bdc3c7;
                border-radius: 10px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
    
    def update_results(self, results: List[WasteDetectionResult]):
        """
        更新检测结果
        
        Args:
            results: 检测结果列表
        """
        # 清除旧结果
        for i in reversed(range(self.content_layout.count())):
            child = self.content_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if not results:
            self.no_result_label.show()
            self.content_area.hide()
            return
        
        self.no_result_label.hide()
        self.content_area.show()
        
        # 添加新结果
        for i, result in enumerate(results):
            result_item = self._create_result_item(result, i + 1)
            self.content_layout.addWidget(result_item)
        
        self.content_layout.addStretch()
    
    def _create_result_item(self, result: WasteDetectionResult, index: int) -> QFrame:
        """
        创建结果项
        
        Args:
            result: 检测结果
            index: 索引
            
        Returns:
            结果项组件
        """
        item_frame = QFrame()
        item_layout = QVBoxLayout(item_frame)
        item_layout.setContentsMargins(10, 10, 10, 10)
        item_layout.setSpacing(5)
        
        # 标题行
        title_layout = QHBoxLayout()
        
        # 序号
        index_label = QLabel(f"#{index}")
        index_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        index_label.setStyleSheet(f"color: {result.color}; padding: 5px;")
        
        # 分类名称
        category_label = QLabel(result.waste_category)
        category_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        category_label.setStyleSheet(f"color: {result.color};")
        
        # 置信度
        confidence_label = QLabel(f"{result.confidence:.1%}")
        confidence_label.setFont(QFont("Microsoft YaHei", 10))
        confidence_label.setStyleSheet("color: #7f8c8d;")
        
        title_layout.addWidget(index_label)
        title_layout.addWidget(category_label)
        title_layout.addStretch()
        title_layout.addWidget(confidence_label)
        
        # 置信度进度条
        confidence_bar = QProgressBar()
        confidence_bar.setRange(0, 100)
        confidence_bar.setValue(int(result.confidence * 100))
        confidence_bar.setFixedHeight(8)
        confidence_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {result.color};
                border-radius: 3px;
            }}
        """)
        
        # 指导文本
        guidance_label = QLabel(result.guidance)
        guidance_label.setFont(QFont("Microsoft YaHei", 11))
        guidance_label.setWordWrap(True)
        guidance_label.setStyleSheet("""
            background-color: rgba(52, 152, 219, 0.1);
            padding: 8px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        """)
        
        item_layout.addLayout(title_layout)
        item_layout.addWidget(confidence_bar)
        item_layout.addWidget(guidance_label)
        
        # 设置样式
        item_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid {result.color}40;
                border-radius: 8px;
                margin: 2px;
            }}
        """)
        
        return item_frame


class GuidanceWidget(QWidget):
    """垃圾投放指导主界面"""
    
    # 信号定义
    voice_toggle_clicked = Signal(bool)  # 语音切换信号
    
    def __init__(self):
        """初始化指导界面"""
        super().__init__()
        
        self.config_manager = get_config_manager()
        self.voice_guide = get_voice_guide()
        
        # 分类卡片
        self.category_cards = {}
        
        # 定时器
        self.clear_timer = QTimer()
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self._clear_guidance)
        
        self._setup_ui()
        self._load_categories()
        
        # 播放欢迎语音
        QTimer.singleShot(1000, self.voice_guide.speak_welcome)
    
    def _setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # 左侧：分类指导区域
        left_widget = self._create_categories_area()
        
        # 右侧：检测结果区域
        right_widget = self._create_detection_area()
        
        main_layout.addWidget(left_widget, 3)
        main_layout.addWidget(right_widget, 2)
    
    def _create_categories_area(self) -> QWidget:
        """创建分类指导区域"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: rgba(248, 249, 250, 0.95);
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("垃圾分类指导")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))  # 减小字体大小
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        title_label.setWordWrap(True)  # 允许标题换行
        
        # 分类卡片网格
        self.categories_scroll = QScrollArea()
        self.categories_scroll.setWidgetResizable(True)
        self.categories_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.categories_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.categories_widget = QWidget()
        self.categories_layout = QGridLayout(self.categories_widget)
        self.categories_layout.setContentsMargins(10, 10, 10, 10)
        self.categories_layout.setSpacing(15)
        
        self.categories_scroll.setWidget(self.categories_widget)
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        
        # 语音开关
        self.voice_button = QPushButton("🔊 语音指导")
        self.voice_button.setFont(QFont("Microsoft YaHei", 10))
        self.voice_button.setCheckable(True)
        self.voice_button.setChecked(True)
        self.voice_button.clicked.connect(self._toggle_voice)
        self.voice_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
            QPushButton:!checked {
                background-color: #95a5a6;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        controls_layout.addWidget(self.voice_button)
        controls_layout.addStretch()
        
        layout.addWidget(title_label)
        layout.addWidget(self.categories_scroll)
        layout.addLayout(controls_layout)
        
        return widget
    
    def _create_detection_area(self) -> QWidget:
        """创建检测结果区域"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: rgba(248, 249, 250, 0.95);
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 检测结果组件
        self.detection_result_widget = DetectionResultWidget()
        
        layout.addWidget(self.detection_result_widget)
        
        return widget
    
    def _load_categories(self):
        """加载垃圾分类"""
        waste_categories = self.config_manager.get_waste_categories()
        
        row = 0
        col = 0
        max_cols = 2
        
        for category, info in waste_categories.items():
            card = CategoryCard(category, info)
            self.category_cards[category] = card
            
            self.categories_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def update_detection_result(self, result: Dict[str, Any]):
        """更新检测结果"""
        try:
            # 处理不同格式的检测结果
            if isinstance(result, dict):
                # 运动检测结果格式
                if 'detection_method' in result and result['detection_method'] == 'motion_detection':
                    category = result.get('category', '未知')
                    confidence = result.get('confidence', 0.0)
                    description = result.get('description', '')
                    image_path = result.get('image_path', '')
                    
                    # 创建检测结果对象
                    detection_result = WasteDetectionResult(
                        category=category,
                        confidence=confidence,
                        bbox=[0, 0, 100, 100],  # 运动检测没有具体边界框
                        description=description
                    )
                    
                    # 更新显示
                    self._update_result_display([detection_result])
                    
                    # 显示捕获的图片路径
                    if image_path:
                        self.logger.info(f"运动检测图片: {image_path}")
                    
                else:
                    # RKNN检测结果格式
                    self._update_result_display(result)
            else:
                # 直接传递结果列表
                self._update_result_display(result)
                
        except Exception as e:
            self.logger.error(f"更新检测结果失败: {e}")
    
    def _update_result_display(self, results):
        """更新结果显示"""
        if not results:
            self.result_widget.clear_results()
            return
        
        # 清空之前的结果
        self.result_widget.clear_results()
        
        # 添加新结果
        for result in results:
            if hasattr(result, 'category'):
                # WasteDetectionResult对象
                self.result_widget.add_result(
                    category=result.category,
                    confidence=result.confidence,
                    description=result.description
                )
            elif isinstance(result, dict):
                # 字典格式
                self.result_widget.add_result(
                    category=result.get('category', '未知'),
                    confidence=result.get('confidence', 0.0),
                    description=result.get('description', '')
                )
        
        # 播放语音指导
        if results and hasattr(self, 'voice_guide') and self.voice_guide:
            if hasattr(results[0], 'category'):
                category = results[0].category
            else:
                category = results[0].get('category', '未知')
            self.voice_guide.speak_guidance(category)
    
    def _play_detection_guidance(self, results: List[WasteDetectionResult]):
        """播放检测指导语音"""
        if len(results) == 1:
            result = results[0]
            self.voice_guide.speak_guidance(result.waste_category, result.guidance)
        elif len(results) > 1:
            self.voice_guide.speak_multiple_items(len(results))
            # 播放第一个结果的指导
            self.voice_guide.speak_guidance(results[0].waste_category, results[0].guidance)
    
    def _clear_guidance(self):
        """清除指导显示"""
        self._update_result_display([])
    
    def _toggle_voice(self):
        """切换语音功能"""
        enabled = self.voice_button.isChecked()
        self.voice_guide.enable_voice(enabled)
        
        # 更新按钮文本
        if enabled:
            self.voice_button.setText("🔊 语音指导")
        else:
            self.voice_button.setText("🔇 静音模式")
        
        # 发送信号
        self.voice_toggle_clicked.emit(enabled)
    
    def show_error(self, error_message: str):
        """显示错误信息"""
        # 这里可以添加错误显示逻辑
        if self.voice_button.isChecked():
            self.voice_guide.speak_error(error_message) 