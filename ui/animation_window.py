#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动画窗口 - 废弃物AI识别指导投放系统
提供直观的动画反馈，指导用户正确投放垃圾
"""

import os
import logging
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QMovie, QScreen, QPixmap, QKeySequence, QShortcut, QFont


class AnimationWindow(QWidget):
    """动画窗口类"""
    
    # 动画状态枚举
    STATE_STANDBY = "standby"           # 待机状态
    STATE_DETECTING = "detecting"       # 识别中状态
    STATE_RECYCLABLE = "recyclable"     # 可回收物
    STATE_OTHER = "other"               # 其他垃圾
    STATE_KITCHEN = "kitchen"           # 厨余垃圾
    STATE_HAZARDOUS = "hazardous"       # 有害垃圾
    STATE_HINT = "hint"                 # 提示状态
    
    # 信号定义
    window_closed = Signal()  # 窗口关闭信号
    
    def __init__(self, parent=None):
        """初始化动画窗口"""
        super().__init__(parent)
        
        # 初始化日志记录器
        self.logger = logging.getLogger(__name__)
        
        # 动画文件映射（根据实际文件名更新）
        self.animation_files = {
            self.STATE_STANDBY: "待机.gif",
            self.STATE_DETECTING: "识别.gif",
            self.STATE_RECYCLABLE: "1.gif",      # 可回收物 -> 左侧投放
            self.STATE_OTHER: "4.gif",        # 其他垃圾 -> 中间投放
            self.STATE_KITCHEN: "3.gif",         # 厨余垃圾 -> 右侧投放
            self.STATE_HAZARDOUS: "2.gif",    # 有害垃圾 -> 中间投放
            self.STATE_HINT: "提示.gif"
        }
        
        # 动画资源路径
        self.animation_dir = Path(__file__).parent.parent / "res" / "gif"
        
        # 当前状态（初始化为None，确保第一次设置状态时能正确加载动画）
        self.current_state = None
        self.current_movie: Optional[QMovie] = None
        
        # 定时器
        self.standby_timer = QTimer()  # 待机定时器（10分钟无操作返回待机）
        self.hint_timer = QTimer()     # 提示定时器（识别完成后10分钟显示提示）
        
        # 初始化UI
        self._setup_ui()
        self._setup_timers()
        self._setup_shortcuts()

        # 启动时显示待机动画
        self.set_standby_state()

        self.logger.info("动画窗口初始化完成")
    
    def _setup_ui(self):
        """设置UI"""
        # 设置窗口属性 - 无边框全屏
        self.setWindowFlags(
            Qt.FramelessWindowHint |      # 无边框
            Qt.WindowStaysOnTopHint |     # 置顶显示
            Qt.Tool                       # 工具窗口，不在任务栏显示
        )
        
        # 设置窗口背景透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 获取屏幕尺寸并设置窗口大小
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            self.setGeometry(screen_geometry)
            self.logger.info(f"动画窗口设置为全屏: {screen_geometry.width()}x{screen_geometry.height()}")
        else:
            # 备用尺寸
            self.resize(1920, 1080)
            self.logger.warning("无法获取屏幕尺寸，使用默认尺寸")
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建动画显示区域（占据大部分空间）
        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.setStyleSheet("background: transparent;")
        self.animation_label.setScaledContents(True)

        # 创建文字信息显示区域
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        # 使用点字号，避免固定像素字体
        self.info_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        self.info_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.8);
                color: white;
                font-weight: bold;
                padding: 20px;
                border-radius: 15px;
                margin: 20px;
            }
        """)
        self.info_label.hide()  # 默认隐藏

        # 添加到布局（文字信息置顶，动画区域占据剩余空间）
        main_layout.addWidget(self.info_label, 0, Qt.AlignHCenter)  # 顶部居中显示提示
        main_layout.addWidget(self.animation_label, 1)  # 拉伸因子为1
        
        # 设置窗口标题（虽然不显示，但便于调试）
        self.setWindowTitle("垃圾分类动画指导")
    
    def _setup_timers(self):
        """设置定时器"""
        # 待机定时器 - 10分钟无操作返回待机
        self.standby_timer.setSingleShot(True)
        self.standby_timer.timeout.connect(self._on_standby_timeout)

        # 提示定时器 - 识别完成后10分钟显示提示
        self.hint_timer.setSingleShot(True)
        self.hint_timer.timeout.connect(self._on_hint_timeout)

    def _setup_shortcuts(self):
        """设置快捷键"""
        # 注意：F11和Ctrl+Alt+A快捷键由主窗口管理，确保全局有效
        # 这里只设置ESC快捷键用于隐藏窗口（仅在窗口获得焦点时有效）

        # ESC 快捷键：隐藏动画窗口（仅在窗口获得焦点时有效）
        self.hide_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.hide_shortcut.activated.connect(self.hide_window)

        self.logger.info("动画窗口快捷键设置完成: ESC(隐藏)")
    
    def _load_animation(self, state: str) -> bool:
        """
        加载指定状态的动画
        
        Args:
            state: 动画状态
            
        Returns:
            是否加载成功
        """
        try:
            # 获取动画文件名
            filename = self.animation_files.get(state)
            if not filename:
                self.logger.error(f"未找到状态 {state} 对应的动画文件")
                return False
            
            # 构建完整路径
            animation_path = self.animation_dir / filename
            
            # 检查文件是否存在
            if not animation_path.exists():
                self.logger.error(f"动画文件不存在: {animation_path}")
                # 尝试显示占位图片
                self._show_placeholder(state)
                return False
            
            # 停止当前动画
            if self.current_movie:
                self.current_movie.stop()
                self.current_movie.deleteLater()
            
            # 创建新的QMovie对象
            self.current_movie = QMovie(str(animation_path))
            
            # 检查动画是否有效
            if not self.current_movie.isValid():
                self.logger.error(f"无效的动画文件: {animation_path}")
                self.current_movie.deleteLater()
                self.current_movie = None
                self._show_placeholder(state)
                return False
            
            # 清除之前的文字内容和样式
            self.animation_label.setText("")
            self.animation_label.setStyleSheet("background: transparent;")

            # 设置动画到标签
            self.animation_label.setMovie(self.current_movie)

            # 开始播放动画
            self.current_movie.start()

            self.logger.info(f"成功加载动画: {filename} (状态: {state})")
            return True
            
        except Exception as e:
            self.logger.error(f"加载动画失败: {e}")
            self._show_placeholder(state)
            return False
    
    def _show_placeholder(self, state: str):
        """显示占位图片"""
        try:
            # 创建简单的文字占位图
            placeholder_text = {
                self.STATE_STANDBY: "待机中...",
                self.STATE_DETECTING: "识别中...",
                self.STATE_RECYCLABLE: "← 可回收物",
                self.STATE_OTHER: "↓ 其他垃圾", 
                self.STATE_KITCHEN: "→ 厨余垃圾",
                self.STATE_HAZARDOUS: "↓ 有害垃圾",
                self.STATE_HINT: "请按指示投放"
            }.get(state, "系统运行中...")
            
            self.animation_label.setMovie(None)
            self.animation_label.setText(placeholder_text)
            # 使用点字号，避免固定像素
            self.animation_label.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
            self.animation_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    background: rgba(0, 0, 0, 0.7);
                    border-radius: 20px;
                    padding: 40px;
                }
            """)
            
            self.logger.info(f"显示占位文字: {placeholder_text}")
            
        except Exception as e:
            self.logger.error(f"显示占位图片失败: {e}")

    def _update_info_display(self, main_category: str, detail_info: str = ""):
        """
        更新信息显示

        Args:
            main_category: 主分类
            detail_info: 详细信息
        """
        try:
            # 构建显示文本
            if detail_info:
                display_text = f"{main_category}\n{detail_info}"
            else:
                display_text = main_category

            # 添加投放指导信息
            direction_mapping = {
                '可回收物': '← 请投放到左侧垃圾桶',
                '其他垃圾': '↓ 请投放到中间垃圾桶',
                '厨余垃圾': '→ 请投放到右侧垃圾桶',
                '有害垃圾': '↓ 请投放到中间垃圾桶'
            }

            direction = direction_mapping.get(main_category, '↓ 请投放到指定垃圾桶')
            display_text += f"\n{direction}"

            # 更新标签内容并显示
            self.info_label.setText(display_text)
            self.info_label.show()

            self.logger.info(f"更新信息显示: {main_category} - {detail_info}")

        except Exception as e:
            self.logger.error(f"更新信息显示失败: {e}")

    def _hide_info_display(self):
        """隐藏信息显示"""
        self.info_label.hide()

    def _reset_timers(self):
        """重置所有定时器"""
        self.standby_timer.stop()
        self.hint_timer.stop()
    
    @Slot()
    def _on_standby_timeout(self):
        """待机超时处理"""
        self.logger.info("10分钟无操作，返回待机状态")
        self.set_standby_state()
    
    @Slot()
    def _on_hint_timeout(self):
        """提示超时处理"""
        self.logger.info("提示时间结束，返回待机状态")
        self.set_standby_state()
    
    def set_standby_state(self):
        """设置待机状态"""
        if self.current_state == self.STATE_STANDBY:
            return

        self.current_state = self.STATE_STANDBY
        self._reset_timers()
        self._hide_info_display()  # 隐藏信息显示
        success = self._load_animation(self.STATE_STANDBY)
        if success:
            self.logger.info("切换到待机状态")
        else:
            self.logger.warning("切换到待机状态失败，显示占位符")
    
    def set_detecting_state(self):
        """设置识别中状态"""
        if self.current_state == self.STATE_DETECTING:
            return

        self.current_state = self.STATE_DETECTING
        self._reset_timers()
        self._hide_info_display()  # 隐藏信息显示
        success = self._load_animation(self.STATE_DETECTING)

        # 启动待机定时器（10分钟后返回待机）
        self.standby_timer.start(10 * 60 * 1000)  # 10分钟

        if success:
            self.logger.info("切换到识别中状态")
        else:
            self.logger.warning("切换到识别中状态失败，显示占位符")
    
    def set_result_state(self, category: str):
        """
        设置识别结果状态

        Args:
            category: 垃圾分类（支持层级格式）
        """
        # 解析层级分类，获取主分类和详细信息
        if '-' in category:
            parts = category.split('-')
            main_category = parts[0]
            detail_info = '-'.join(parts[1:]) if len(parts) > 1 else ""
        else:
            main_category = category
            detail_info = ""

        # 映射到动画状态
        state_mapping = {
            '可回收物': self.STATE_RECYCLABLE,
            '其他垃圾': self.STATE_OTHER,
            '厨余垃圾': self.STATE_KITCHEN,
            '有害垃圾': self.STATE_HAZARDOUS
        }

        new_state = state_mapping.get(main_category, self.STATE_OTHER)

        if self.current_state == new_state:
            # 即使状态相同，也要更新文字信息
            self._update_info_display(main_category, detail_info)
            return

        self.current_state = new_state
        self._reset_timers()
        success = self._load_animation(new_state)

        # 显示垃圾类型信息
        self._update_info_display(main_category, detail_info)

        # 5秒后切换到提示状态
        QTimer.singleShot(5000, self.set_hint_state)

        if success:
            self.logger.info(f"切换到识别结果状态: {main_category} -> {new_state}")
        else:
            self.logger.warning(f"切换到识别结果状态失败: {main_category} -> {new_state}，显示占位符")
    
    def set_hint_state(self):
        """设置提示状态"""
        if self.current_state == self.STATE_HINT:
            return

        self.current_state = self.STATE_HINT
        self._reset_timers()
        self._hide_info_display()  # 隐藏信息显示
        success = self._load_animation(self.STATE_HINT)

        # 启动提示定时器（10分钟后返回待机）
        self.hint_timer.start(10 * 60 * 1000)  # 10分钟

        if success:
            self.logger.info("切换到提示状态")
        else:
            self.logger.warning("切换到提示状态失败，显示占位符")
    
    def reset_standby_timer(self):
        """重置待机定时器（用户有操作时调用）"""
        if self.standby_timer.isActive():
            self.standby_timer.start(10 * 60 * 1000)  # 重新开始10分钟倒计时
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止所有定时器
            self._reset_timers()
            
            # 停止动画
            if self.current_movie:
                self.current_movie.stop()
                self.current_movie.deleteLater()
                self.current_movie = None
            
            # 发送关闭信号
            self.window_closed.emit()
            
            self.logger.info("动画窗口已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭动画窗口时出错: {e}")
        
        super().closeEvent(event)
    
    def show_window(self):
        """显示窗口"""
        self.show()
        self.raise_()  # 提升到最前面
        self.activateWindow()  # 激活窗口
        self.logger.info("动画窗口已显示")
    
    def hide_window(self):
        """隐藏窗口"""
        self.hide()
        self.logger.info("动画窗口已隐藏")

    def toggle_visibility(self):
        """切换窗口显示/隐藏状态"""
        if self.isVisible():
            self.hide_window()
        else:
            self.show_window()
        self.logger.info(f"动画窗口切换: {'显示' if self.isVisible() else '隐藏'}")

    def is_visible(self):
        """检查窗口是否可见"""
        return self.isVisible()
