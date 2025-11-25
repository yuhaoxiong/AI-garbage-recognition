#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面 - 废弃物AI识别指导投放系统
整合摄像头显示、AI检测和指导界面
"""

import cv2
import numpy as np
import logging
from typing import Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QSplitter, QStatusBar,
                              QMenuBar, QMessageBox, QApplication, QDialog, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtGui import QImage, QPixmap, QFont, QAction, QKeySequence, QShortcut

# 导入工作器模块
try:
    from worker.waste_detection_worker import WasteDetectionWorker, WasteDetectionResult
except ImportError:
    logging.warning("废弃物检测工作器导入失败，将使用模拟模式")
    WasteDetectionWorker = None
    WasteDetectionResult = None

# 导入动画窗口
try:
    from ui.animation_window import AnimationWindow
except ImportError:
    logging.warning("动画窗口导入失败，将禁用动画功能")
    AnimationWindow = None

try:
    from worker.io_control_worker import IOControlWorker
except ImportError:
    logging.warning("IO控制工作器导入失败，IO功能将被禁用")
    IOControlWorker = None

try:
    from worker.motion_detection_worker import MotionDetectionWorker
except ImportError:
    logging.warning("运动检测工作器导入失败，运动检测功能将被禁用")
    MotionDetectionWorker = None

# 导入UI模块
try:
    from ui.guidance_widget import GuidanceWidget
except ImportError:
    logging.error("指导界面组件导入失败")
    GuidanceWidget = None

try:
    from ui.dynamic_status_widget import DynamicStatusWidget
except ImportError:
    logging.warning("动态状态组件导入失败，状态显示功能将被禁用")
    DynamicStatusWidget = None

try:
    from ui.config_dialog import ConfigDialog
except ImportError:
    logging.warning("参数配置对话框导入失败，配置功能将被禁用")
    ConfigDialog = None

try:
    from ui.motion_detection_test_window import MotionDetectionTestWindow
except ImportError:
    logging.warning("运动检测测试窗口导入失败，测试功能将被禁用")
    MotionDetectionTestWindow = None

# 导入工具模块
try:
    from utils.config_manager import get_config_manager
except ImportError:
    logging.error("配置管理器导入失败")
    get_config_manager = None

try:
    from utils.voice_integration import get_voice_integration_manager
    VOICE_AVAILABLE = True
except ImportError:
    logging.warning("增强语音模块导入失败，语音功能将被禁用")
    get_voice_integration_manager = None
    VOICE_AVAILABLE = False

try:
    from utils.voice_assistant import VoiceAssistantWorker
    VOICE_ASSISTANT_AVAILABLE = True
except Exception:
    VOICE_ASSISTANT_AVAILABLE = False


class CameraDisplayWidget(QFrame):
    """摄像头显示组件"""
    
    def __init__(self):
        """初始化摄像头显示组件"""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # 标题
        title_label = QLabel("实时摄像头")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding: 12px;")
        
        # 视频显示区域 - 优化尺寸
        self.video_label = QLabel()
        self.video_label.setMinimumSize(480, 360)  # 16:9 比例
        # 移除最大尺寸限制，允许在高分辨率显示器上自适应放大
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)
        # 使用点字号，避免像素字体在高DPI下失真
        self.video_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #34495e;
                border: 3px solid #3498db;
                border-radius: 12px;
                color: white;
                font-weight: bold;
            }
        """)
        self.video_label.setText("摄像头未启动")
        
        # 状态信息
        self.status_label = QLabel("状态: 未连接")
        self.status_label.setFont(QFont("Microsoft YaHei", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 8px;")

        # 运动状态显示区域
        self.motion_status_frame = QFrame()
        self.motion_status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        motion_status_layout = QHBoxLayout(self.motion_status_frame)
        motion_status_layout.setContentsMargins(10, 5, 10, 5)

        # 运动状态图标和文本
        self.motion_status_icon = QLabel("🔍")
        self.motion_status_icon.setFont(QFont("Microsoft YaHei", 16))
        self.motion_status_icon.setAlignment(Qt.AlignCenter)

        self.motion_status_text = QLabel("等待运动检测...")
        self.motion_status_text.setFont(QFont("Microsoft YaHei", 11))
        self.motion_status_text.setStyleSheet("color: #6c757d;")

        motion_status_layout.addWidget(self.motion_status_icon)
        motion_status_layout.addWidget(self.motion_status_text, 1)

        # 添加到布局
        layout.addWidget(title_label)
        layout.addWidget(self.video_label, 1)  # 拉伸因子
        layout.addWidget(self.status_label)
        layout.addWidget(self.motion_status_frame)

    def resizeEvent(self, event):
        """自适应缩放当前帧以匹配标签尺寸（提高窗口缩放体验）"""
        super().resizeEvent(event)
        try:
            current_pixmap = self.video_label.pixmap()
            if current_pixmap:
                scaled = current_pixmap.scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.video_label.setPixmap(scaled)
        except Exception:
            pass
    
    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            CameraDisplayWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ecf0f1, stop:1 #bdc3c7);
                border-radius: 15px;
                border: 2px solid #95a5a6;
            }
        """)
    
    def update_frame(self, frame: np.ndarray):
        """更新视频帧"""
        try:
            if frame is None:
                self.video_label.setText("摄像头未启动")
                return
            
            # 转换颜色格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # 创建QImage
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 缩放到适合显示区域的尺寸
            label_size = self.video_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.logger.error(f"更新视频帧失败: {e}")
            self.video_label.setText("视频显示错误")
    
    def show_error(self, error_message: str):
        """显示错误信息"""
        try:
            self.video_label.setText(f"错误: {error_message}")
            self.status_label.setText(f"摄像头错误: {error_message}")
            self.logger.error(f"摄像头错误: {error_message}")
        except Exception as e:
            self.logger.error(f"显示错误信息失败: {e}")
    
    def update_status(self, status: str, fps: float = 0, resolution: tuple = None):
        """更新状态信息"""
        try:
            status_text = f"状态: {status}"
            if fps > 0:
                status_text += f" | FPS: {fps:.1f}"
            if resolution:
                status_text += f" | 分辨率: {resolution[0]}x{resolution[1]}"
            
            self.status_label.setText(status_text)
            
        except Exception as e:
            self.logger.error(f"更新状态失败: {e}")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化配置管理器
        try:
            self.config_manager = get_config_manager() if get_config_manager else None
        except Exception as e:
            self.logger.error(f"配置管理器初始化失败: {e}")
            self.config_manager = None
        
        # 初始化语音指导
        try:
            if VOICE_AVAILABLE:
                self.voice_manager = get_voice_integration_manager()
                self.voice_guide = self.voice_manager.get_voice_guide()
            else:
                self.voice_manager = None
                self.voice_guide = None
        except Exception as e:
            self.logger.error(f"语音指导初始化失败: {e}")
            self.voice_manager = None
            self.voice_guide = None
        
        # 工作器实例
        self.detection_worker = None
        self.io_control_worker = None
        self.motion_detection_worker = None
        
        # 动态状态组件
        self.dynamic_status_widget = None
        
        # 运动检测测试窗口
        self.motion_test_window = None

        # 动画窗口
        self.animation_window = None

        # 运动检测暂停控制
        self._motion_detection_resume_timer = None
        self._motion_detection_prev_enabled = False
        self._motion_detection_resume_needed = False

        # 显示模式标志
        self.show_detection_result = False

        # 最后的检测结果（用于在等待下次检测时保持显示）
        self.last_detection_result = None

        # 语音助手
        self.voice_assistant = None

        # 初始化界面和功能
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_connections()
        self._init_workers()
        self._init_animation_window()
        self._init_voice_assistant()

        # 延迟播放欢迎语音
        if self.voice_manager:
            QTimer.singleShot(2000, lambda: self.voice_manager.handle_scene('system_start'))
    
    def _setup_ui(self):
        """设置UI"""
        try:
            # 设置窗口属性
            if self.config_manager:
                ui_config = self.config_manager.get_ui_config()
                self.setWindowTitle(ui_config.window_title)
                
                # 优化窗口大小
                self.resize(ui_config.window_size['width'], ui_config.window_size['height'])
            else:
                self.setWindowTitle('废弃物AI识别指导投放系统')
                self.resize(1200, 800)
            
            # 设置窗口最小尺寸
            self.setMinimumSize(900, 650)
            
            # 窗口居中显示
            self._center_window()
            
            # 主布局
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            main_layout = QHBoxLayout(central_widget)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(20)
            
            # 创建分割器 - 左右两栏布局
            self.splitter = QSplitter(Qt.Horizontal)
            
            # 左侧：摄像头显示
            self.camera_widget = CameraDisplayWidget()
            self.camera_widget.setMinimumWidth(500)
            
            # 右侧：动态状态显示组件
            if DynamicStatusWidget:
                self.dynamic_status_widget = DynamicStatusWidget()
                self.dynamic_status_widget.setMinimumWidth(450)
                # 保持原有的指导界面作为备用（可选）
                if GuidanceWidget:
                    # 传递语音实例避免重复初始化
                    self.guidance_widget = GuidanceWidget(voice_guide=self.voice_guide)
                    self.guidance_widget.hide()  # 初始隐藏
                else:
                    self.guidance_widget = self._create_fallback_guidance_widget()
                    self.guidance_widget.hide()
            else:
                # 创建简单的替代界面
                self.dynamic_status_widget = self._create_fallback_status_widget()
                self.guidance_widget = self._create_fallback_guidance_widget()
            
            # 添加到分割器
            self.splitter.addWidget(self.camera_widget)
            self.splitter.addWidget(self.dynamic_status_widget)
            
            # 设置分割比例
            self.splitter.setSizes([600, 600])
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 1)
            
            # 设置分割器样式
            self.splitter.setStyleSheet("""
                QSplitter::handle {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #bdc3c7, stop:1 #95a5a6);
                    width: 4px;
                    margin: 2px;
                    border-radius: 2px;
                }
                QSplitter::handle:hover {
                    background: #3498db;
                }
            """)
            
            main_layout.addWidget(self.splitter)
            
        except Exception as e:
            self.logger.error(f"UI设置失败: {e}")
            # 创建最基本的界面
            self._create_minimal_ui()
    
    def _center_window(self):
        """窗口居中显示"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                window_geometry = self.frameGeometry()
                center_point = screen_geometry.center()
                window_geometry.moveCenter(center_point)
                self.move(window_geometry.topLeft())
        except Exception as e:
            self.logger.error(f"窗口居中失败: {e}")
    
    def _create_fallback_guidance_widget(self):
        """创建备用指导界面"""
        widget = QFrame()
        layout = QVBoxLayout(widget)
        
        label = QLabel("指导界面加载失败\n请检查相关模块")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Microsoft YaHei", 16))
        label.setStyleSheet("color: #e74c3c; padding: 20px;")
        
        layout.addWidget(label)
        return widget

    def _create_fallback_status_widget(self):
        """创建备用状态显示组件"""
        widget = QFrame()
        layout = QVBoxLayout(widget)

        label = QLabel("动态状态组件加载失败\n请检查相关模块")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Microsoft YaHei", 16))
        label.setStyleSheet("color: #e74c3c; padding: 20px;")

        layout.addWidget(label)
        return widget

    def _create_minimal_ui(self):
        """创建最小化界面（错误恢复）"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        error_label = QLabel("界面初始化失败\n系统运行在最小模式")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setFont(QFont("Microsoft YaHei", 18))
        error_label.setStyleSheet("color: #e74c3c; padding: 50px;")
        
        layout.addWidget(error_label)
        
        self.logger.error("使用最小化界面模式")
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 退出动作
        exit_action = QAction('退出(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置(&S)')
        
        # 语音设置
        voice_action = QAction('语音设置(&V)', self)
        voice_action.triggered.connect(self._show_voice_settings)
        settings_menu.addAction(voice_action)
        
        # 摄像头设置
        camera_action = QAction('摄像头设置(&C)', self)
        camera_action.triggered.connect(self._show_camera_settings)
        settings_menu.addAction(camera_action)

        # 参数配置
        config_action = QAction('参数配置(&P)', self)
        config_action.triggered.connect(self._show_config_dialog)
        settings_menu.addAction(config_action)
        
        # IO控制开关
        self.io_control_action = QAction('IO控制(&I)', self)
        self.io_control_action.setCheckable(True)
        
        # 从配置中读取IO控制状态
        if self.config_manager:
            io_config = self.config_manager.get_io_config()
            io_enabled = io_config.enable_io_control
        else:
            io_enabled = True
        self.io_control_action.setChecked(io_enabled)
        
        self.io_control_action.triggered.connect(self._toggle_io_control)
        settings_menu.addAction(self.io_control_action)

        # 语音助手开关
        self.voice_assistant_action = QAction('语音助手(&A)', self)
        self.voice_assistant_action.setCheckable(True)
        va_enabled = False
        try:
            if self.config_manager:
                va_enabled = self.config_manager.get_voice_assistant_config().enable_voice_assistant
        except Exception:
            pass
        self.voice_assistant_action.setChecked(bool(va_enabled))
        self.voice_assistant_action.triggered.connect(self._toggle_voice_assistant)
        settings_menu.addAction(self.voice_assistant_action)
        
        # 动态状态显示（已集成到主界面）
        # 不再需要独立的动画窗口菜单项
        
        # 运动检测测试界面
        motion_test_action = QAction('运动检测测试界面(&T)', self)
        motion_test_action.triggered.connect(self._show_motion_test_window)
        settings_menu.addAction(motion_test_action)
        
        # 检测菜单
        detection_menu = menubar.addMenu("检测")
        
        # 开始/停止检测
        self.start_detection_action = QAction("开始检测", self)
        self.start_detection_action.triggered.connect(self._start_detection)
        detection_menu.addAction(self.start_detection_action)
        
        self.stop_detection_action = QAction("停止检测", self)
        self.stop_detection_action.triggered.connect(self._stop_detection)
        self.stop_detection_action.setEnabled(False)
        detection_menu.addAction(self.stop_detection_action)
        
        detection_menu.addSeparator()
        
        # 检测模式切换
        self.rknn_mode_action = QAction("RKNN模式", self)
        self.rknn_mode_action.setCheckable(True)
        self.rknn_mode_action.setChecked(False)  # 默认不选中RKNN模式
        self.rknn_mode_action.triggered.connect(self._switch_to_rknn_mode)
        detection_menu.addAction(self.rknn_mode_action)

        self.motion_mode_action = QAction("运动检测模式", self)
        self.motion_mode_action.setCheckable(True)
        self.motion_mode_action.setChecked(True)  # 默认选中运动检测模式
        self.motion_mode_action.triggered.connect(self._switch_to_motion_mode)
        detection_menu.addAction(self.motion_mode_action)
        
        detection_menu.addSeparator()
        
        # 运动检测控制
        self.enable_motion_detection_action = QAction("启用运动检测", self)
        self.enable_motion_detection_action.setCheckable(True)
        self.enable_motion_detection_action.triggered.connect(self._toggle_motion_detection)
        detection_menu.addAction(self.enable_motion_detection_action)
        
        self.reset_motion_background_action = QAction("重置运动背景", self)
        self.reset_motion_background_action.triggered.connect(self._reset_motion_background)
        detection_menu.addAction(self.reset_motion_background_action)
        
        detection_menu.addSeparator()
        
        # 显示模式切换
        self.show_detection_result_action = QAction("显示运动检测结果", self)
        self.show_detection_result_action.setCheckable(True)
        self.show_detection_result_action.triggered.connect(self._toggle_detection_result_display)
        detection_menu.addAction(self.show_detection_result_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
        # 关于
        about_action = QAction('关于(&A)', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        # 使用说明
        help_action = QAction('使用说明(&H)', self)
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
    
    def _setup_status_bar(self):
        """设置状态栏"""
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_label = QLabel("就绪")
        self.camera_status_label = QLabel("摄像头: 未连接")
        self.detection_status_label = QLabel("检测: 停止")
        self.io_status_label = QLabel("IO控制: 禁用")
        self.motion_status_label = QLabel("运动检测: 禁用")
        self.voice_status_label = QLabel("语音: 启用")
        self.assistant_status_label = QLabel("助手: 关闭")
        
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.camera_status_label)
        self.status_bar.addPermanentWidget(self.detection_status_label)
        self.status_bar.addPermanentWidget(self.io_status_label)
        self.status_bar.addPermanentWidget(self.motion_status_label)
        self.status_bar.addPermanentWidget(self.voice_status_label)
        self.status_bar.addPermanentWidget(self.assistant_status_label)
    
    def _setup_connections(self):
        """设置信号连接"""
        # 指导界面信号
        if GuidanceWidget:
            self.guidance_widget.voice_toggle_clicked.connect(self._on_voice_toggle)
    
    def _init_workers(self):
        """初始化工作器"""
        try:
            # 初始化基础检测工作器
            if WasteDetectionWorker:
                self.detection_worker = WasteDetectionWorker()

                # 连接信号
                self.detection_worker.frame_processed.connect(self.camera_widget.update_frame)
                self.detection_worker.detection_result.connect(self._on_detection_result)
                self.detection_worker.fps_updated.connect(self.camera_widget.update_status)
                self.detection_worker.error_occurred.connect(self._on_detection_error)
                self.detection_worker.status_changed.connect(self._on_detection_status_changed)

                # 启动检测工作器（但不启用AI检测，默认使用运动检测模式）
                self.detection_worker.start_detection()
                # 禁用RKNN检测，使用运动检测模式
                self.detection_worker.enable_io_detection(False)

                self.status_label.setText("系统就绪 - 运动检测模式")
                self.camera_widget.update_status("摄像头已启动", fps=getattr(self.detection_worker, 'current_fps', 0))
            else:
                self.logger.warning("废弃物检测工作器未导入，无法启动")
                self.status_label.setText("系统就绪 (AI检测禁用)")
                self.camera_widget.update_status("摄像头已启动", fps=0)

            # 初始化运动检测工作器
            self._init_motion_detection_worker()

            # 初始化IO控制工作器
            self._init_io_control_worker()

            # 初始化动态状态组件连接
            self._init_dynamic_status_connections()

        except Exception as e:
            self.logger.error(f"初始化检测工作器失败: {e}")
            self.status_label.setText(f"初始化失败: {e}")
            self.camera_widget.update_status("摄像头已启动", fps=0)
            self.camera_widget.show_error(str(e))
    
    def _init_io_control_worker(self):
        """初始化IO控制工作器"""
        try:
            # 检查是否启用IO控制
            if self.config_manager:
                io_config = self.config_manager.get_io_config()
                if not io_config.enable_io_control:
                    self.logger.info("IO控制已禁用")
                    return
            else:
                self.logger.info("配置管理器不可用，IO控制已禁用")
                return
            
            self.io_control_worker = IOControlWorker()
            
            # 连接IO控制信号
            if self.io_control_worker:
                self.io_control_worker.ir_signal_detected.connect(self._on_ir_signal_detected)
                self.io_control_worker.ir_signal_lost.connect(self._on_ir_signal_lost)
                self.io_control_worker.detection_trigger.connect(self._on_detection_trigger)
            
            # 启动IO控制
            if self.io_control_worker:
                self.io_control_worker.start()
            
            self.logger.info("IO控制工作器初始化成功")
            
        except Exception as e:
            self.logger.error(f"初始化IO控制工作器失败: {e}")
            # IO控制失败不影响主要功能，继续运行
    
    def _init_motion_detection_worker(self):
        """初始化运动检测工作器"""
        try:
            self.logger.info("🔧 开始初始化运动检测工作器...")

            # 检查MotionDetectionWorker是否成功导入
            if MotionDetectionWorker is None:
                self.logger.error("❌ MotionDetectionWorker类未成功导入，运动检测功能不可用")
                self.status_label.setText("错误: 运动检测模块导入失败")
                return
            else:
                self.logger.info("✅ MotionDetectionWorker类导入成功")

            # 检查是否启用运动检测
            if self.config_manager:
                self.logger.info("✅ 配置管理器可用")
                motion_config = self.config_manager.get_motion_detection_config()
                self.logger.info(f"📊 运动检测配置: enable_motion_detection={motion_config.enable_motion_detection}")

                if not motion_config.enable_motion_detection:
                    self.logger.info("⚠️ 运动检测已在配置中禁用")
                    self.status_label.setText("运动检测已在配置中禁用")
                    return
            else:
                self.logger.error("❌ 配置管理器不可用，运动检测已禁用")
                self.status_label.setText("错误: 配置管理器不可用")
                return

            # 检查基础检测工作器
            if not self.detection_worker:
                self.logger.error("❌ 基础检测工作器不存在，无法初始化运动检测")
                self.status_label.setText("错误: 基础检测工作器不存在")
                return
            else:
                self.logger.info("✅ 基础检测工作器可用")
            
            try:
                self.logger.info("🔄 创建运动检测工作器实例...")
                self.motion_detection_worker = MotionDetectionWorker(self.detection_worker)
                self.logger.info("✅ 运动检测工作器实例创建成功")
            except Exception as e:
                self.logger.error(f"❌ 创建运动检测工作器实例失败: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
                self.status_label.setText("错误: 运动检测工作器创建失败")
                return

            # 连接运动检测信号
            try:
                self.logger.info("🔄 连接运动检测信号...")
                self.motion_detection_worker.motion_detected.connect(self._on_motion_detected)
                self.motion_detection_worker.image_captured.connect(self._on_image_captured)
                self.motion_detection_worker.api_result_received.connect(self._on_api_result_received)
                self.motion_detection_worker.detection_completed.connect(self._on_motion_detection_completed)
                self.motion_detection_worker.error_occurred.connect(self._on_motion_detection_error)
                self.motion_detection_worker.motion_state_changed.connect(self._on_motion_state_changed)
                self.logger.info("✅ 信号连接成功")
            except Exception as e:
                self.logger.error(f"❌ 连接运动检测信号失败: {e}")
                self.status_label.setText("错误: 运动检测信号连接失败")
                return

            # 启动运动检测
            try:
                self.logger.info("🔄 启动运动检测工作器线程...")
                self.motion_detection_worker.start()
                # 自动启用运动检测，无需用户手动点击开始按钮
                self.motion_detection_worker.enable_detection(True)
                self.logger.info("✅ 运动检测工作器已启动并自动启用")

                # 更新状态显示
                self.status_label.setText("系统就绪 - 运动检测已启动")
                self.motion_status_label.setText("运动检测: 运行中")

                # 更新菜单状态
                if hasattr(self, 'start_detection_action'):
                    self.start_detection_action.setEnabled(False)
                if hasattr(self, 'stop_detection_action'):
                    self.stop_detection_action.setEnabled(True)
                if hasattr(self, 'motion_mode_action'):
                    self.motion_mode_action.setChecked(True)

                self.logger.info("✅ 运动检测工作器初始化完全成功并已自动启动")
            except Exception as e:
                self.logger.error(f"❌ 启动运动检测工作器线程失败: {e}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
                self.status_label.setText("错误: 运动检测工作器启动失败")
                return
            
        except Exception as e:
            self.logger.error(f"❌ 初始化运动检测工作器失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            self.status_label.setText(f"错误: 运动检测初始化失败 - {str(e)}")
            # 运动检测失败不影响主要功能，继续运行
            self.motion_detection_worker = None
    
    def _init_dynamic_status_connections(self):
        """初始化动态状态组件连接"""
        try:
            if self.dynamic_status_widget:
                # 连接状态变化信号
                self.dynamic_status_widget.status_changed.connect(self._on_status_changed)
                self.logger.info("动态状态组件连接成功")

        except Exception as e:
            self.logger.error(f"动态状态组件连接失败: {e}")

    def _init_animation_window(self):
        """初始化动画窗口"""
        try:
            if AnimationWindow:
                self.animation_window = AnimationWindow(self)

                # 连接信号
                self.animation_window.window_closed.connect(self._on_animation_window_closed)

                # 设置主窗口的快捷键
                self._setup_animation_shortcuts()

                # 显示动画窗口
                self.animation_window.show_window()

                self.logger.info("动画窗口初始化完成")
            else:
                self.logger.warning("动画窗口类不可用，跳过初始化")

        except Exception as e:
            self.logger.error(f"初始化动画窗口失败: {e}")
            self.animation_window = None

    def _init_voice_assistant(self):
        """初始化语音助手"""
        try:
            if not VOICE_ASSISTANT_AVAILABLE or not self.config_manager:
                return
            vac = self.config_manager.get_voice_assistant_config()
            if not vac.enable_voice_assistant:
                self.assistant_status_label.setText("助手: 关闭")
                return
            self.voice_assistant = VoiceAssistantWorker()
            # 信号连接
            self.voice_assistant.status_changed.connect(self._on_va_status_changed)
            self.voice_assistant.wakeup_state_changed.connect(self._on_va_wakeup_state_changed)
            self.voice_assistant.asr_text_ready.connect(self._on_va_asr_text)
            self.voice_assistant.reply_ready.connect(self._on_va_reply_ready)
            # 启动
            self.voice_assistant.start()
            self.assistant_status_label.setText("助手: 等待唤醒")
        except Exception as e:
            self.logger.error(f"初始化语音助手失败: {e}")

    def _toggle_voice_assistant(self, checked: bool):
        try:
            # 更新配置
            if self.config_manager:
                self.config_manager.update_config('system', 'voice_assistant.enable_voice_assistant', checked)
            # 停止/启动
            if checked:
                if not self.voice_assistant and VOICE_ASSISTANT_AVAILABLE:
                    self._init_voice_assistant()
                elif self.voice_assistant:
                    self.voice_assistant.start()
                self.assistant_status_label.setText("助手: 等待唤醒")
            else:
                if self.voice_assistant:
                    self.voice_assistant.stop()
                self.assistant_status_label.setText("助手: 关闭")
        except Exception as e:
            self.logger.error(f"切换语音助手失败: {e}")

    # === 语音助手回调 ===
    def _on_va_status_changed(self, text: str):
        try:
            self.status_label.setText(text)
        except Exception:
            pass

    def _on_va_wakeup_state_changed(self, awakened: bool):
        try:
            self.assistant_status_label.setText("助手: 对话中" if awakened else "助手: 等待唤醒")
        except Exception:
            pass

    def _on_va_asr_text(self, text: str):
        try:
            self.status_label.setText(f"您说: {text}")
        except Exception:
            pass

    def _on_va_reply_ready(self, reply: str):
        try:
            # 显示在状态栏简要提示
            self.status_label.setText("助手: 已回答")
            # 通过语音播报
            vac = self.config_manager.get_voice_assistant_config() if self.config_manager else None
            if vac and getattr(vac, 'response_with_tts', True) and self.voice_manager:
                try:
                    self.voice_manager.get_voice_guide().speak(reply)
                except Exception:
                    pass
            # 同时在右侧指导区域显示（可选）
            if hasattr(self, 'guidance_widget') and self.guidance_widget:
                try:
                    self.guidance_widget.update_detection_result({
                        'category': '语音助手',
                        'description': reply
                    })
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"处理助手回复失败: {e}")

    def _setup_animation_shortcuts(self):
        """设置动画窗口快捷键"""
        try:
            # F11 快捷键：切换动画窗口显示/隐藏
            self.animation_toggle_shortcut = QShortcut(QKeySequence("F11"), self)
            self.animation_toggle_shortcut.activated.connect(self._toggle_animation_window)

            # Ctrl+Alt+A 快捷键：切换动画窗口显示/隐藏（备用）
            self.animation_toggle_shortcut_alt = QShortcut(QKeySequence("Ctrl+Alt+A"), self)
            self.animation_toggle_shortcut_alt.activated.connect(self._toggle_animation_window)

            self.logger.info("动画窗口快捷键设置完成: F11/Ctrl+Alt+A")

        except Exception as e:
            self.logger.error(f"设置动画窗口快捷键失败: {e}")

    def _suspend_motion_detection(self, delay: float = 1.0, reason: str = ""):
        """在界面快速切换时暂时关闭运动检测，避免误触发"""
        if not self.motion_detection_worker:
            return
        try:
            worker = self.motion_detection_worker
            was_enabled = bool(getattr(worker, "is_enabled", False))
            if not was_enabled:
                self._motion_detection_prev_enabled = False
                self._motion_detection_resume_needed = False
                return

            worker.enable_detection(False)
            self._motion_detection_prev_enabled = True
            self._motion_detection_resume_needed = True

            if reason:
                self.logger.debug(f"暂停运动检测: {reason}")

            if self._motion_detection_resume_timer is None:
                self._motion_detection_resume_timer = QTimer(self)
                self._motion_detection_resume_timer.setSingleShot(True)
                self._motion_detection_resume_timer.timeout.connect(self._resume_motion_detection)
            else:
                self._motion_detection_resume_timer.stop()

            delay_ms = max(int(delay * 1000), 100)
            self._motion_detection_resume_timer.start(delay_ms)

        except Exception as e:
            self.logger.warning(f"暂停运动检测失败: {e}")
            self._motion_detection_prev_enabled = False
            self._motion_detection_resume_needed = False

    def _resume_motion_detection(self):
        """界面切换结束后恢复运动检测"""
        if not self.motion_detection_worker:
            self._motion_detection_prev_enabled = False
            self._motion_detection_resume_needed = False
            return

        if not self._motion_detection_prev_enabled or not self._motion_detection_resume_needed:
            return

        try:
            self.motion_detection_worker.reset_background()
            self.motion_detection_worker.enable_detection(True)
            self.logger.debug("运动检测已恢复")
        except Exception as e:
            self.logger.warning(f"恢复运动检测失败: {e}")
        finally:
            self._motion_detection_prev_enabled = False
            self._motion_detection_resume_needed = False

    def _toggle_animation_window(self):
        """切换动画窗口显示状态"""
        try:
            self._suspend_motion_detection(1.0, 'animation_window_toggle')
            if self.animation_window:
                self.animation_window.toggle_visibility()
                status = "显示" if self.animation_window.isVisible() else "隐藏"
                self.status_label.setText(f"动画窗口已{status}")
                self.logger.info(f"通过快捷键切换动画窗口: {status}")
            else:
                # 动画窗口不存在，重新创建并显示
                self.logger.info("动画窗口不存在，重新创建")
                self._init_animation_window()
                if self.animation_window:
                    self.status_label.setText("动画窗口已显示")
                    self.logger.info("通过快捷键重新创建并显示动画窗口")

        except Exception as e:
            self.logger.error(f"切换动画窗口失败: {e}")

    @Slot()
    def _on_animation_window_closed(self):
        """动画窗口关闭处理"""
        self.logger.info("动画窗口已关闭")
        self.animation_window = None

    @Slot()
    def _on_ir_signal_detected(self):
        """红外信号检测到"""
        self.logger.info("红外信号检测到")
        self.status_label.setText("检测到用户接近，准备识别...")
    
    @Slot()
    def _on_ir_signal_lost(self):
        """红外信号丢失"""
        self.logger.info("红外信号丢失")
        self.status_label.setText("用户离开，停止识别")
    
    @Slot(bool)
    def _on_detection_trigger(self, enabled: bool):
        """检测触发信号"""
        if self.detection_worker:
            self.detection_worker.enable_io_detection(enabled)
            
            if enabled:
                self.logger.info("开始AI检测")
                self.status_label.setText("正在进行AI检测...")
            else:
                self.logger.info("停止AI检测")
                self.status_label.setText("AI检测已停止")
    
    @Slot(list)
    def _on_detection_result(self, results: list):
        """
        处理检测结果
        
        Args:
            results: 检测结果列表
        """
        # 更新指导界面
        if GuidanceWidget and results:
            self.guidance_widget.update_detection_result(results)
        
        # 更新状态
        if results:
            categories = [r.waste_category for r in results]
            self.status_label.setText(f"检测到: {', '.join(categories)}")
            
            # 动态状态组件会自动处理结果显示
            # 不再需要独立的动画窗口
        else:
            self.status_label.setText("未检测到废弃物")
    
    @Slot(str)
    def _on_detection_error(self, error_message: str):
        """处理检测错误"""
        self.logger.error(f"检测错误: {error_message}")
        self.status_label.setText(f"检测错误: {error_message}")
        self.camera_widget.update_status("视频显示错误", fps=0)
        self.camera_widget.show_error(error_message)
        if GuidanceWidget:
            self.guidance_widget.show_error(error_message)
    
    @Slot(str)
    def _on_detection_status_changed(self, status: str):
        """处理检测状态变化"""
        self.detection_status_label.setText(f"检测: {status}")
    
    @Slot(bool)
    def _on_voice_toggle(self, enabled: bool):
        """处理语音开关"""
        status = "启用" if enabled else "禁用"
        self.voice_status_label.setText(f"语音: {status}")
    
    def update_motion_status(self, status_text: str, icon: str = "🔍", color: str = "#6c757d"):
        """更新运动状态显示"""
        try:
            if hasattr(self.camera_widget, 'motion_status_icon'):
                self.camera_widget.motion_status_icon.setText(icon)
            if hasattr(self.camera_widget, 'motion_status_text'):
                self.camera_widget.motion_status_text.setText(status_text)
                self.camera_widget.motion_status_text.setStyleSheet(f"color: {color};")
        except Exception as e:
            self.logger.warning(f"更新运动状态显示失败: {e}")

    @Slot(dict)
    def _on_motion_state_changed(self, state_info: dict):
        """处理运动状态机状态变化"""
        try:
            state = state_info.get('state', 'no_motion')
            state_duration = state_info.get('state_duration', 0)
            stability_duration = state_info.get('stability_duration', 0)
            last_area = state_info.get('last_area', 0)

            # 根据状态机状态更新显示
            if state == 'no_motion':
                # 如果有上一次的检测结果，显示它；否则显示等待状态
                if self.last_detection_result and self.last_detection_result.get('category'):
                    category_text = self.last_detection_result.get('category', '未知')
                    specific_item = self.last_detection_result.get('specific_item')
                    main_category = self.last_detection_result.get('main_category')
                    if not main_category and isinstance(category_text, str) and '-' in category_text:
                        main_category = category_text.split('-')[0]
                    display_text = specific_item or category_text
                    if display_text and main_category and display_text != main_category:
                        status_text = f"上次识别: {display_text}（{main_category}）"
                    else:
                        status_text = f"上次识别: {display_text or '未知'}"
                    self.update_motion_status(status_text, "📋", "#6c757d")
                else:
                    self.update_motion_status("等待物体进入检测区域...", "🔍", "#6c757d")
            elif state == 'entering':
                self.update_motion_status(f"检测到物体进入 (面积: {last_area:.0f})", "👁️", "#fd7e14")
            elif state == 'present_moving':
                self.update_motion_status(f"物体移动中... (持续: {state_duration:.1f}s)", "🔄", "#17a2b8")
            elif state == 'present_stable':
                if stability_duration > 0:
                    self.update_motion_status(f"物体稳定中... (稳定: {stability_duration:.1f}s)", "⏱️", "#28a745")
                else:
                    self.update_motion_status("物体开始稳定...", "📍", "#ffc107")
            elif state == 'leaving':
                self.update_motion_status("物体正在离开...", "👋", "#6f42c1")

            # 更新状态栏
            self.motion_status_label.setText(f"运动检测: {state} ({state_duration:.1f}s)")

        except Exception as e:
            self.logger.warning(f"处理运动状态变化失败: {e}")

    @Slot()
    def _on_motion_detected(self):
        """处理运动检测信号"""
        self.status_label.setText("运动检测: 检测到运动")
        self.logger.info("检测到运动")

        # 更新运动状态显示
        self.update_motion_status("检测到运动！正在分析...", "👁️", "#fd7e14")

        # 更新动态状态组件
        if self.dynamic_status_widget:
            self.dynamic_status_widget.set_detected_state()

        # 更新动画窗口状态
        if self.animation_window:
            self.animation_window.set_detecting_state()

        # 播放运动检测语音
        if self.voice_manager:
            self.voice_manager.handle_scene('motion_detected')
    
    @Slot(str)
    def _on_image_captured(self, image_path: str):
        """处理图片捕获信号"""
        self.logger.info(f"图片已捕获: {image_path}")

        # 更新运动状态显示
        self.update_motion_status("图片已捕获，正在识别...", "📷", "#0d6efd")

        # 更新动态状态组件为识别中状态，并显示捕获的图片
        if self.dynamic_status_widget:
            self.dynamic_status_widget.set_recognizing_state(30)  # 开始识别，进度30%
            # 在动态状态组件中显示最近捕获的图片
            self.dynamic_status_widget.show_captured_image(image_path)

        # 播放图片捕获语音
        if self.voice_manager:
            self.voice_manager.handle_scene('image_captured')
    
    @Slot(dict)
    def _on_api_result_received(self, result: dict):
        """处理API结果信号"""
        self.logger.info(f"收到API结果: {result}")

        if not result:
            self.update_motion_status("识别失败，请重试", "❌", "#dc3545")
            self.last_detection_result = None
            return

        category_raw = result.get('category', '其他垃圾-其他类-未知物品')
        category_parts = [part.strip() for part in str(category_raw).split('-') if part.strip()]
        main_category = category_parts[0] if category_parts else '其他垃圾'
        sub_category = category_parts[1] if len(category_parts) > 1 else '其他类'
        specific_item = category_parts[2] if len(category_parts) > 2 else ''

        composition = result.get('composition') or ''
        degradation_time = result.get('degradation_time') or ''
        recycling_value = result.get('recycling_value') or ''

        # 构建统一描述文本，兼容旧组件
        description_parts = []
        if composition:
            description_parts.append(f"组成成分：{composition}")
        if degradation_time:
            description_parts.append(f"降解时间：{degradation_time}")
        if recycling_value:
            description_parts.append(f"回收建议：{recycling_value}")
        description_text = "\n".join(description_parts) if description_parts else "暂未提供详细的组成和处理信息。"

        normalized_result = dict(result)
        normalized_result['category'] = str(category_raw)
        normalized_result['full_category'] = str(category_raw)
        normalized_result['main_category'] = main_category
        normalized_result['sub_category'] = sub_category
        normalized_result['specific_item'] = specific_item
        normalized_result['description'] = description_text
        normalized_result['detection_method'] = 'API调用'

        display_name = specific_item or main_category or category_raw

        # 更新运动状态显示 - 保持识别结果显示
        if normalized_result.get('category'):
            self.update_motion_status(f"识别完成: {display_name}", "✅", "#28a745")
            # 保存最后的识别结果，用于在等待下次检测时显示
            self.last_detection_result = normalized_result
        else:
            self.update_motion_status("识别失败，请重试", "❌", "#dc3545")
            self.last_detection_result = None

        # 更新动态状态组件为识别成功状态
        if self.dynamic_status_widget:
            self.dynamic_status_widget.set_success_state(normalized_result)

        # 更新动画窗口状态
        if self.animation_window and normalized_result.get('category'):
            self.animation_window.set_result_state(normalized_result['category'])

        # 不再自动重置状态，让状态机控制状态显示

        # 在右侧检测结果区域显示API结果（备用指导界面）
        if self.guidance_widget:
            try:
                self.guidance_widget.update_detection_result(normalized_result)
                self.status_label.setText(f"API识别结果: {display_name}")
                self.logger.info(f"API结果已显示在检测结果区域: {normalized_result['category']}")
            except Exception as e:
                self.logger.error(f"显示API结果失败: {e}")
                self.status_label.setText(f"API结果显示错误: {str(e)}")
    
    @Slot(dict)
    def _on_motion_detection_completed(self, detection_result: dict):
        """处理运动检测完成信号"""
        self.logger.info(f"运动检测完成: {detection_result}")

        # 重置动态状态组件到等待状态（延迟5秒）
        if self.dynamic_status_widget:
            QTimer.singleShot(5000, self.dynamic_status_widget.reset_to_waiting)

        # 更新指导界面
        if self.guidance_widget:
            self.guidance_widget.update_detection_result(detection_result)
        
        # 动态状态组件已在API结果回调中处理，这里不需要额外处理
        
        # 播放语音指导（统一在这里处理，避免重复）
        if self.voice_manager:
            category = detection_result.get('category', '未知')
            self.voice_manager.handle_scene(
                'recognition_success',
                category=category,
                specific_item=detection_result.get('specific_item'),
                composition=detection_result.get('composition'),
                degradation_time=detection_result.get('degradation_time'),
                recycling_value=detection_result.get('recycling_value')
            )
    
    @Slot(str)
    def _on_motion_detection_error(self, error: str):
        """处理运动检测错误信号"""
        self.logger.error(f"运动检测错误: {error}")
        self.status_label.setText(f"运动检测错误: {error}")

        # 播放错误语音
        if self.voice_manager:
            self.voice_manager.handle_scene('system_error', error_message="运动检测出现问题")
    
    def _reset_motion_background(self):
        """重置运动检测背景"""
        if self.motion_detection_worker:
            self.motion_detection_worker.reset_background()
            self.logger.info("运动检测背景已重置")
    
    def _switch_to_rknn_mode(self):
        """切换到RKNN模式"""
        self.rknn_mode_action.setChecked(True)
        self.motion_mode_action.setChecked(False)
        
        # 停止运动检测
        if self.motion_detection_worker:
            self.motion_detection_worker.enable_detection(False)
        
        # 启用RKNN检测
        if self.detection_worker:
            self.detection_worker.enable_io_detection(True)
        
        self.detection_status_label.setText("检测: RKNN模式")
        self.logger.info("切换到RKNN检测模式")
    
    def _switch_to_motion_mode(self):
        """切换到运动检测模式"""
        self.motion_mode_action.setChecked(True)
        self.rknn_mode_action.setChecked(False)
        
        # 停止RKNN检测
        if self.detection_worker:
            self.detection_worker.enable_io_detection(False)
        
        # 启用运动检测
        if self.motion_detection_worker:
            self.motion_detection_worker.enable_detection(True)
        
        self.detection_status_label.setText("检测: 运动检测模式")
        self.logger.info("切换到运动检测模式")
    
    def _toggle_motion_detection(self):
        """切换运动检测状态"""
        if not self.motion_detection_worker:
            self.logger.warning("运动检测工作器未初始化")
            return
        
        enabled = self.enable_motion_detection_action.isChecked()
        self.motion_detection_worker.enable_detection(enabled)
        
        status = "启用" if enabled else "禁用"
        self.motion_status_label.setText(f"运动检测: {status}")
        self.logger.info(f"运动检测已{status}")
    
    def _start_detection(self):
        """开始检测"""
        try:
            self.logger.info("🚀 用户点击开始检测按钮")

            # 检查模式选择
            rknn_checked = self.rknn_mode_action.isChecked()
            motion_checked = self.motion_mode_action.isChecked()

            self.logger.info(f"📊 当前模式状态: RKNN={rknn_checked}, 运动检测={motion_checked}")

            if rknn_checked:
                self.logger.info("🎯 启动RKNN检测模式...")
                if self.detection_worker:
                    self.detection_worker.enable_io_detection(True)
                    self.start_detection_action.setEnabled(False)
                    self.stop_detection_action.setEnabled(True)
                    self.detection_status_label.setText("检测: RKNN运行中")
                    self.logger.info("✅ RKNN检测已启动")
                else:
                    self.logger.error("❌ RKNN检测工作器不存在")
                    self.status_label.setText("错误: RKNN检测工作器未初始化")

            elif motion_checked:
                self.logger.info("🎯 启动运动检测模式...")
                if self.motion_detection_worker:
                    # 检查工作器状态
                    is_running = getattr(self.motion_detection_worker, 'is_running', False)
                    self.logger.info(f"📊 运动检测工作器运行状态: {is_running}")

                    if not is_running:
                        self.logger.warning("⚠️ 运动检测工作器未运行，尝试启动...")
                        try:
                            self.motion_detection_worker.start()
                            self.logger.info("✅ 运动检测工作器已启动")
                        except Exception as e:
                            self.logger.error(f"❌ 启动运动检测工作器失败: {e}")

                    # 启用检测
                    self.motion_detection_worker.enable_detection(True)
                    self.start_detection_action.setEnabled(False)
                    self.stop_detection_action.setEnabled(True)
                    self.detection_status_label.setText("检测: 运动检测运行中")
                    self.status_label.setText("运动检测已启动 - 等待运动触发")
                    self.logger.info("✅ 运动检测已启动")
                else:
                    self.logger.error("❌ 运动检测工作器不存在")
                    self.status_label.setText("错误: 运动检测工作器未初始化")
            else:
                self.logger.warning("⚠️ 没有选择任何检测模式")
                self.status_label.setText("请先选择检测模式（RKNN或运动检测）")

        except Exception as e:
            self.logger.error(f"❌ 开始检测失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            self.status_label.setText(f"开始检测失败: {str(e)}")
    
    def _stop_detection(self):
        """停止检测"""
        try:
            self.logger.info("🛑 用户点击停止检测按钮")

            # 停止RKNN检测
            if self.detection_worker:
                self.detection_worker.enable_io_detection(False)
                self.logger.info("✅ RKNN检测已停止")

            # 停止运动检测
            if self.motion_detection_worker:
                self.motion_detection_worker.enable_detection(False)
                self.logger.info("✅ 运动检测已停止")

            # 更新UI状态
            self.start_detection_action.setEnabled(True)
            self.stop_detection_action.setEnabled(False)
            self.detection_status_label.setText("检测: 停止")
            self.status_label.setText("检测已停止")
            self.logger.info("✅ 所有检测已停止")

        except Exception as e:
            self.logger.error(f"❌ 停止检测失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            self.status_label.setText(f"停止检测失败: {str(e)}")
    
    def _show_voice_settings(self):
        """显示语音设置对话框"""
        # 这里可以实现语音设置对话框
        QMessageBox.information(self, "语音设置", "语音设置功能正在开发中...")
    
    def _show_camera_settings(self):
        """显示摄像头设置对话框"""
        # 这里可以实现摄像头设置对话框
        QMessageBox.information(self, "摄像头设置", "摄像头设置功能正在开发中...")
    
    def _toggle_io_control(self, checked: bool):
        """切换IO控制状态"""
        try:
            # 更新配置
            if self.config_manager:
                self.config_manager.update_config('system', 'io_control.enable_io_control', checked)
            
            # 重启IO控制工作器
            if self.io_control_worker:
                self.io_control_worker.stop()
                self.io_control_worker = None
            
            if checked:
                self._init_io_control_worker()
                self.io_status_label.setText("IO: 启用")
                self.logger.info("IO控制已启用")
            else:
                self.io_status_label.setText("IO: 禁用")
                self.logger.info("IO控制已禁用")
                
        except Exception as e:
            self.logger.error(f"切换IO控制失败: {e}")
            QMessageBox.warning(self, "错误", f"切换IO控制失败: {e}")
    
    def _show_status_info(self):
        """显示状态信息"""
        if self.dynamic_status_widget:
            current_state = getattr(self.dynamic_status_widget, 'current_state', 'unknown')
            QMessageBox.information(self, "状态信息", f"当前状态: {current_state}\n\n动态状态显示已集成到主界面右侧")
        else:
            QMessageBox.warning(self, "错误", "动态状态组件未初始化")

    def _show_config_dialog(self):
        """显示参数配置对话框"""
        if ConfigDialog is None:
            QMessageBox.warning(self, "错误", "参数配置功能不可用")
            return

        try:
            config_dialog = ConfigDialog(self)

            # 连接配置更新信号
            config_dialog.config_updated.connect(self._on_config_updated)

            # 显示对话框
            if config_dialog.exec() == QDialog.Accepted:
                self.logger.info("配置对话框已确认")
            else:
                self.logger.info("配置对话框已取消")

        except Exception as e:
            self.logger.error(f"显示配置对话框失败: {e}")
            QMessageBox.warning(self, "错误", f"显示配置对话框失败: {e}")

    @Slot(dict)
    def _on_config_updated(self, config: dict):
        """配置更新回调"""
        try:
            self.logger.info("收到配置更新信号")

            # 这里可以根据需要重新初始化相关组件
            # 例如：重新初始化摄像头、更新UI设置等

            # 显示配置更新成功的消息
            QMessageBox.information(self, "成功", "配置已更新，部分设置可能需要重启程序后生效")

        except Exception as e:
            self.logger.error(f"处理配置更新失败: {e}")
            QMessageBox.warning(self, "错误", f"处理配置更新失败: {e}")
    
    @Slot(str)
    def _on_status_changed(self, status: str):
        """状态变化回调"""
        self.logger.info(f"识别状态变化: {status}")
        # 可以在这里添加额外的状态处理逻辑
    
    def _show_about(self):
        """显示关于对话框"""
        about_text = """
        <h3>废弃物AI识别指导投放系统</h3>
        <p>版本: 1.0.0</p>
        <p>基于AI技术的智能垃圾分类指导系统</p>
        <p>支持实时摄像头检测和语音指导</p>
        <br>
        <p>技术栈:</p>
        <ul>
        <li>PySide6 - 用户界面</li>
        <li>OpenCV - 图像处理</li>
        <li>RKNN - AI推理引擎</li>
        <li>PyTTSx3 - 语音合成</li>
        </ul>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def _show_help(self):
        """显示使用说明"""
        help_text = """
        <h3>使用说明</h3>
        <p><b>1. 系统启动</b></p>
        <p>系统启动后会自动打开摄像头并开始AI检测</p>
        
        <p><b>2. 垃圾识别</b></p>
        <p>将废弃物放在摄像头前，系统会自动识别并分类</p>
        
        <p><b>3. 投放指导</b></p>
        <p>系统会显示垃圾分类结果和投放指导信息</p>
        <p>同时播放语音指导（可通过按钮关闭）</p>
        
        <p><b>4. 分类说明</b></p>
        <p>• 可回收物（蓝色）：塑料瓶、纸张等</p>
        <p>• 有害垃圾（红色）：电池、药品等</p>
        <p>• 湿垃圾（棕色）：食物残渣、果皮等</p>
        <p>• 干垃圾（黑色）：其他垃圾</p>
        
        <p><b>5. 注意事项</b></p>
        <p>• 保持摄像头清洁</p>
        <p>• 单个物品效果更佳</p>
        <p>• 光线充足有助于识别</p>
        """
        QMessageBox.information(self, "使用说明", help_text)
    
    def _show_motion_test_window(self):
        """显示运动检测测试窗口"""
        try:
            if not MotionDetectionTestWindow:
                QMessageBox.warning(self, "提示", "运动检测测试窗口模块未加载")
                return
            
            # 检查检测工作器是否启动
            if not self.detection_worker or not self.detection_worker.running:
                reply = QMessageBox.question(
                    self, 
                    "提示", 
                    "运动检测测试需要摄像头数据。\n是否现在启动检测？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._start_detection()
                    # 等待一下让检测启动
                    import time
                    time.sleep(0.5)
                else:
                    return
            
            if not self.motion_test_window:
                # 创建测试窗口，传入检测工作器（用于获取摄像头帧）
                detection_worker = self.detection_worker if self.detection_worker else None
                
                self.motion_test_window = MotionDetectionTestWindow(self, detection_worker)
                
                # 连接信号，用于在主界面显示检测结果
                self.motion_test_window.detection_result_ready.connect(self._on_test_detection_result)
                
                logging.info("运动检测测试窗口已创建")
            
            self.motion_test_window.show()
            self.motion_test_window.raise_()
            self.motion_test_window.activateWindow()
            
        except Exception as e:
            logging.error(f"显示运动检测测试窗口失败: {e}")
            QMessageBox.critical(self, "错误", f"显示测试窗口失败:\n{e}")
    
    def _toggle_detection_result_display(self):
        """切换主界面显示模式"""
        self.show_detection_result = self.show_detection_result_action.isChecked()
        
        if self.show_detection_result:
            logging.info("主界面切换为显示运动检测结果")
            
            # 暂时断开检测工作器的帧信号连接，避免显示冲突
            if self.detection_worker:
                try:
                    self.detection_worker.frame_processed.disconnect(self.camera_widget.update_frame)
                    logging.info("已断开检测工作器的帧信号连接")
                except:
                    pass  # 如果已经断开则忽略
            
            # 如果测试窗口未打开，提示用户
            if not self.motion_test_window or not self.motion_test_window.isVisible():
                QMessageBox.information(
                    self, 
                    "信息", 
                    "已切换为显示运动检测结果模式\n请先打开运动检测测试界面并开始测试"
                )
        else:
            logging.info("主界面切换为显示原始摄像头画面")
            
            # 重新连接检测工作器的帧信号
            if self.detection_worker:
                try:
                    self.detection_worker.frame_processed.connect(self.camera_widget.update_frame)
                    logging.info("已重新连接检测工作器的帧信号")
                except:
                    pass  # 如果已经连接则忽略
    
    def _on_test_detection_result(self, result_frame: np.ndarray):
        """处理测试窗口的检测结果"""
        try:
            if self.show_detection_result and result_frame is not None:
                # 检查结果帧的格式
                if len(result_frame.shape) == 3 and result_frame.shape[2] == 3:
                    # 在主界面显示检测结果
                    self.camera_widget.update_frame(result_frame)
                else:
                    logging.warning(f"运动检测结果帧格式不正确: {result_frame.shape}")
        except Exception as e:
            logging.error(f"显示运动检测结果失败: {e}")
            self.camera_widget.show_error(f"显示运动检测结果失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止检测工作器
            if self.detection_worker:
                self.detection_worker.stop_detection()
            
            # 停止IO控制工作器
            if self.io_control_worker:
                self.io_control_worker.stop()
            
            # 停止运动检测工作器
            if self.motion_detection_worker:
                self.motion_detection_worker.stop()
            
            # 动态状态组件已集成到主界面，无需单独关闭
            
            # 关闭动画窗口
            if self.animation_window:
                self.animation_window.close()

            # 关闭运动检测测试窗口
            if self.motion_test_window:
                self.motion_test_window.close()

            # 停止语音
            if self.voice_manager:
                self.voice_manager.cleanup()
            # 停止语音助手
            try:
                if self.voice_assistant:
                    self.voice_assistant.stop()
            except Exception:
                pass
            
            self.logger.info("应用程序正常关闭")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"关闭应用程序时出错: {e}")
            event.accept()  # 强制关闭
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_F11:
            # F11切换全屏
            self._suspend_motion_detection(1.0, 'fullscreen_toggle')
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            # ESC退出全屏
            self._suspend_motion_detection(0.8, 'exit_fullscreen')
            self.showNormal()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """
        窗口大小变化事件处理
        
        Args:
            event: 大小变化事件
        """
        super().resizeEvent(event)
        
        # 动态调整分割器比例
        if hasattr(self, 'splitter'):
            window_width = self.width()
            
            # 根据窗口大小调整左右分割比例
            if window_width < 1000:
                # 小窗口：摄像头稍大
                camera_width = int(window_width * 0.55)
                guidance_width = int(window_width * 0.45)
            else:
                # 大窗口：平均分配
                camera_width = int(window_width * 0.5)
                guidance_width = int(window_width * 0.5)
            
            self.splitter.setSizes([camera_width, guidance_width]) 
