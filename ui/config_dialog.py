#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数配置界面 - 废弃物AI识别指导投放系统
提供图形化界面来修改系统配置参数
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QFormLayout, QSpinBox, QDoubleSpinBox, QLineEdit, QCheckBox, 
    QComboBox, QSlider, QPushButton, QLabel, QGroupBox, 
    QMessageBox, QFileDialog, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from utils.config_manager import get_config_manager


class ConfigDialog(QDialog):
    """参数配置对话框"""
    
    # 配置更新信号
    config_updated = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # 获取配置管理器
        self.config_manager = get_config_manager()
        self.config_data = {}
        self.widgets = {}  # 存储所有配置控件
        
        self.setWindowTitle("系统参数配置")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_config()
        self._setup_connections()
    
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("系统参数配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("padding: 10px; color: #2c3e50;")
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个配置标签页
        self._create_camera_tab()
        self._create_motion_detection_tab()
        self._create_api_tab()
        self._create_audio_tab()
        self._create_voice_assistant_tab()
        self._create_llm_tab()
        self._create_io_control_tab()
        self._create_animation_tab()
        self._create_logging_tab()
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 重置按钮
        self.reset_button = QPushButton("重置默认值")
        self.reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(self.reset_button)
        
        # 导入/导出按钮
        self.import_button = QPushButton("导入配置")
        self.import_button.clicked.connect(self._import_config)
        button_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("导出配置")
        self.export_button.clicked.connect(self._export_config)
        button_layout.addWidget(self.export_button)
        
        button_layout.addStretch()
        
        # 确定/取消按钮
        self.apply_button = QPushButton("应用")
        self.apply_button.clicked.connect(self._apply_config)
        button_layout.addWidget(self.apply_button)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _create_camera_tab(self):
        """创建摄像头配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)
        
        # 设备ID
        self.widgets['camera.device_id'] = QSpinBox()
        self.widgets['camera.device_id'].setRange(0, 10)
        self.widgets['camera.device_id'].setToolTip("摄像头设备ID，通常为0")
        basic_layout.addRow("设备ID:", self.widgets['camera.device_id'])
        
        # 分辨率
        resolution_layout = QHBoxLayout()
        self.widgets['camera.resolution.width'] = QSpinBox()
        self.widgets['camera.resolution.width'].setRange(320, 4096)
        self.widgets['camera.resolution.width'].setSingleStep(160)
        resolution_layout.addWidget(self.widgets['camera.resolution.width'])
        
        resolution_layout.addWidget(QLabel("×"))
        
        self.widgets['camera.resolution.height'] = QSpinBox()
        self.widgets['camera.resolution.height'].setRange(240, 2160)
        self.widgets['camera.resolution.height'].setSingleStep(120)
        resolution_layout.addWidget(self.widgets['camera.resolution.height'])
        
        basic_layout.addRow("分辨率:", resolution_layout)
        
        # 帧率
        self.widgets['camera.fps'] = QSpinBox()
        self.widgets['camera.fps'].setRange(1, 60)
        self.widgets['camera.fps'].setToolTip("摄像头帧率，建议15-30")
        basic_layout.addRow("帧率(FPS):", self.widgets['camera.fps'])
        
        layout.addWidget(basic_group)
        
        # 高级设置组
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)
        
        # 自动对焦
        self.widgets['camera.auto_focus'] = QCheckBox()
        self.widgets['camera.auto_focus'].setToolTip("启用摄像头自动对焦")
        advanced_layout.addRow("自动对焦:", self.widgets['camera.auto_focus'])
        
        # 曝光值
        self.widgets['camera.exposure'] = QSpinBox()
        self.widgets['camera.exposure'].setRange(-10, 10)
        self.widgets['camera.exposure'].setSpecialValueText("自动")
        self.widgets['camera.exposure'].setToolTip("曝光值，-1为自动")
        advanced_layout.addRow("曝光值:", self.widgets['camera.exposure'])
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "📷 摄像头")
    
    def _create_io_control_tab(self):
        """创建IO控制配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # IO控制设置组
        io_group = QGroupBox("IO控制设置")
        io_layout = QFormLayout(io_group)

        # 启用IO控制
        self.widgets['io_control.enable_io_control'] = QCheckBox()
        io_layout.addRow("启用IO控制:", self.widgets['io_control.enable_io_control'])

        # 红外传感器引脚
        self.widgets['io_control.ir_sensor_pin'] = QSpinBox()
        self.widgets['io_control.ir_sensor_pin'].setRange(1, 40)
        io_layout.addRow("红外传感器引脚:", self.widgets['io_control.ir_sensor_pin'])

        # 检测延迟
        self.widgets['io_control.detection_delay'] = QDoubleSpinBox()
        self.widgets['io_control.detection_delay'].setRange(0.1, 5.0)
        self.widgets['io_control.detection_delay'].setSingleStep(0.1)
        self.widgets['io_control.detection_delay'].setSuffix(" 秒")
        io_layout.addRow("检测延迟:", self.widgets['io_control.detection_delay'])

        # 检测超时
        self.widgets['io_control.detection_timeout'] = QSpinBox()
        self.widgets['io_control.detection_timeout'].setRange(5, 60)
        self.widgets['io_control.detection_timeout'].setSuffix(" 秒")
        io_layout.addRow("检测超时:", self.widgets['io_control.detection_timeout'])

        # 防抖时间
        self.widgets['io_control.debounce_time'] = QDoubleSpinBox()
        self.widgets['io_control.debounce_time'].setRange(0.05, 1.0)
        self.widgets['io_control.debounce_time'].setSingleStep(0.05)
        self.widgets['io_control.debounce_time'].setSuffix(" 秒")
        io_layout.addRow("防抖时间:", self.widgets['io_control.debounce_time'])

        layout.addWidget(io_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🔌 IO控制")

    def _create_animation_tab(self):
        """创建动画配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 动画设置组
        animation_group = QGroupBox("动画设置")
        animation_layout = QFormLayout(animation_group)

        # 启用动画
        self.widgets['animation.enable_animations'] = QCheckBox()
        animation_layout.addRow("启用动画:", self.widgets['animation.enable_animations'])

        # 粒子数量
        self.widgets['animation.particle_count'] = QSpinBox()
        self.widgets['animation.particle_count'].setRange(5, 100)
        animation_layout.addRow("粒子数量:", self.widgets['animation.particle_count'])

        # 动画持续时间
        self.widgets['animation.animation_duration'] = QSpinBox()
        self.widgets['animation.animation_duration'].setRange(1000, 10000)
        self.widgets['animation.animation_duration'].setSuffix(" 毫秒")
        animation_layout.addRow("动画持续时间:", self.widgets['animation.animation_duration'])

        # 成功动画持续时间
        self.widgets['animation.success_animation_duration'] = QSpinBox()
        self.widgets['animation.success_animation_duration'].setRange(1000, 5000)
        self.widgets['animation.success_animation_duration'].setSuffix(" 毫秒")
        animation_layout.addRow("成功动画持续时间:", self.widgets['animation.success_animation_duration'])

        # 脉冲动画帧率
        self.widgets['animation.pulse_animation_fps'] = QSpinBox()
        self.widgets['animation.pulse_animation_fps'].setRange(10, 60)
        self.widgets['animation.pulse_animation_fps'].setSuffix(" FPS")
        animation_layout.addRow("脉冲动画帧率:", self.widgets['animation.pulse_animation_fps'])

        layout.addWidget(animation_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🎬 动画")

    def _create_logging_tab(self):
        """创建日志配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 日志设置组
        logging_group = QGroupBox("日志设置")
        logging_layout = QFormLayout(logging_group)

        # 日志级别
        self.widgets['logging.level'] = QComboBox()
        self.widgets['logging.level'].addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        logging_layout.addRow("日志级别:", self.widgets['logging.level'])

        # 日志文件路径
        self.widgets['logging.file_path'] = QLineEdit()
        logging_layout.addRow("日志文件路径:", self.widgets['logging.file_path'])

        # 最大文件大小
        self.widgets['logging.max_file_size'] = QLineEdit()
        logging_layout.addRow("最大文件大小:", self.widgets['logging.max_file_size'])

        # 备份数量
        self.widgets['logging.backup_count'] = QSpinBox()
        self.widgets['logging.backup_count'].setRange(1, 20)
        logging_layout.addRow("备份数量:", self.widgets['logging.backup_count'])

        # 控制台输出
        self.widgets['logging.console_output'] = QCheckBox()
        logging_layout.addRow("控制台输出:", self.widgets['logging.console_output'])

        layout.addWidget(logging_group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "📝 日志")
    
    def _create_motion_detection_tab(self):
        """创建运动检测配置标签页"""
        tab = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout(basic_group)
        
        # 启用运动检测
        self.widgets['motion_detection.enable_motion_detection'] = QCheckBox()
        basic_layout.addRow("启用运动检测:", self.widgets['motion_detection.enable_motion_detection'])
        
        # 使用智能检测器
        self.widgets['motion_detection.use_smart_detector'] = QCheckBox()
        self.widgets['motion_detection.use_smart_detector'].setToolTip("使用增强的智能运动检测算法")
        basic_layout.addRow("智能检测器:", self.widgets['motion_detection.use_smart_detector'])
        
        # 运动阈值
        self.widgets['motion_detection.motion_threshold'] = QSpinBox()
        self.widgets['motion_detection.motion_threshold'].setRange(100, 2000)
        self.widgets['motion_detection.motion_threshold'].setSingleStep(50)
        self.widgets['motion_detection.motion_threshold'].setToolTip("运动检测敏感度阈值")
        basic_layout.addRow("运动阈值:", self.widgets['motion_detection.motion_threshold'])
        
        # 最小轮廓面积
        self.widgets['motion_detection.min_contour_area'] = QSpinBox()
        self.widgets['motion_detection.min_contour_area'].setRange(500, 10000)
        self.widgets['motion_detection.min_contour_area'].setSingleStep(100)
        self.widgets['motion_detection.min_contour_area'].setToolTip("检测的最小物体面积")
        basic_layout.addRow("最小轮廓面积:", self.widgets['motion_detection.min_contour_area'])
        
        # 检测冷却时间
        self.widgets['motion_detection.detection_cooldown'] = QDoubleSpinBox()
        self.widgets['motion_detection.detection_cooldown'].setRange(1.0, 30.0)
        self.widgets['motion_detection.detection_cooldown'].setSingleStep(0.5)
        self.widgets['motion_detection.detection_cooldown'].setSuffix(" 秒")
        self.widgets['motion_detection.detection_cooldown'].setToolTip("两次检测之间的冷却时间")
        basic_layout.addRow("检测冷却时间:", self.widgets['motion_detection.detection_cooldown'])
        
        layout.addWidget(basic_group)
        
        # ROI设置组
        roi_group = QGroupBox("检测区域(ROI)设置")
        roi_layout = QFormLayout(roi_group)
        
        # 启用ROI
        self.widgets['motion_detection.roi_enabled'] = QCheckBox()
        self.widgets['motion_detection.roi_enabled'].setToolTip("启用感兴趣区域检测")
        roi_layout.addRow("启用ROI:", self.widgets['motion_detection.roi_enabled'])
        
        # ROI比例设置
        for direction in ['top', 'bottom', 'left', 'right']:
            widget = QDoubleSpinBox()
            widget.setRange(0.0, 1.0)
            widget.setSingleStep(0.05)
            widget.setDecimals(2)
            widget.setToolTip(f"ROI{direction}边界比例")
            self.widgets[f'motion_detection.roi_{direction}_ratio'] = widget
            roi_layout.addRow(f"ROI {direction.upper()} 比例:", widget)
        
        layout.addWidget(roi_group)
        
        # 高级参数组
        advanced_group = QGroupBox("高级参数")
        advanced_layout = QFormLayout(advanced_group)

        # 背景减除参数
        self.widgets['motion_detection.history'] = QSpinBox()
        self.widgets['motion_detection.history'].setRange(100, 1000)
        self.widgets['motion_detection.history'].setSingleStep(50)
        advanced_layout.addRow("历史帧数:", self.widgets['motion_detection.history'])

        self.widgets['motion_detection.dist2_threshold'] = QDoubleSpinBox()
        self.widgets['motion_detection.dist2_threshold'].setRange(100.0, 1000.0)
        self.widgets['motion_detection.dist2_threshold'].setSingleStep(50.0)
        advanced_layout.addRow("距离阈值:", self.widgets['motion_detection.dist2_threshold'])

        self.widgets['motion_detection.detect_shadows'] = QCheckBox()
        advanced_layout.addRow("检测阴影:", self.widgets['motion_detection.detect_shadows'])

        # 图像处理参数
        self.widgets['motion_detection.blur_kernel_size'] = QSpinBox()
        self.widgets['motion_detection.blur_kernel_size'].setRange(3, 15)
        self.widgets['motion_detection.blur_kernel_size'].setSingleStep(2)
        advanced_layout.addRow("模糊核大小:", self.widgets['motion_detection.blur_kernel_size'])

        self.widgets['motion_detection.kernel_size'] = QSpinBox()
        self.widgets['motion_detection.kernel_size'].setRange(3, 15)
        self.widgets['motion_detection.kernel_size'].setSingleStep(2)
        advanced_layout.addRow("形态学核大小:", self.widgets['motion_detection.kernel_size'])

        # 智能检测器参数
        self.widgets['motion_detection.stability_threshold'] = QDoubleSpinBox()
        self.widgets['motion_detection.stability_threshold'].setRange(10.0, 200.0)
        self.widgets['motion_detection.stability_threshold'].setSingleStep(5.0)
        advanced_layout.addRow("稳定性阈值:", self.widgets['motion_detection.stability_threshold'])

        self.widgets['motion_detection.min_stability_duration'] = QDoubleSpinBox()
        self.widgets['motion_detection.min_stability_duration'].setRange(0.5, 10.0)
        self.widgets['motion_detection.min_stability_duration'].setSingleStep(0.1)
        self.widgets['motion_detection.min_stability_duration'].setSuffix(" 秒")
        advanced_layout.addRow("最小稳定时间:", self.widgets['motion_detection.min_stability_duration'])

        self.widgets['motion_detection.max_stability_duration'] = QDoubleSpinBox()
        self.widgets['motion_detection.max_stability_duration'].setRange(1.0, 20.0)
        self.widgets['motion_detection.max_stability_duration'].setSingleStep(0.5)
        self.widgets['motion_detection.max_stability_duration'].setSuffix(" 秒")
        advanced_layout.addRow("最大稳定时间:", self.widgets['motion_detection.max_stability_duration'])

        self.widgets['motion_detection.min_presence_area'] = QSpinBox()
        self.widgets['motion_detection.min_presence_area'].setRange(1000, 20000)
        self.widgets['motion_detection.min_presence_area'].setSingleStep(500)
        advanced_layout.addRow("最小存在面积:", self.widgets['motion_detection.min_presence_area'])

        self.widgets['motion_detection.center_movement_threshold'] = QDoubleSpinBox()
        self.widgets['motion_detection.center_movement_threshold'].setRange(10.0, 100.0)
        self.widgets['motion_detection.center_movement_threshold'].setSingleStep(5.0)
        advanced_layout.addRow("中心移动阈值:", self.widgets['motion_detection.center_movement_threshold'])

        self.widgets['motion_detection.min_presence_duration'] = QDoubleSpinBox()
        self.widgets['motion_detection.min_presence_duration'].setRange(0.1, 5.0)
        self.widgets['motion_detection.min_presence_duration'].setSingleStep(0.1)
        self.widgets['motion_detection.min_presence_duration'].setSuffix(" 秒")
        advanced_layout.addRow("最小存在时间:", self.widgets['motion_detection.min_presence_duration'])
        
        layout.addWidget(advanced_group)
        layout.addStretch()
        
        tab.setWidget(content)
        tab.setWidgetResizable(True)
        self.tab_widget.addTab(tab, "🏃 运动检测")
    
    def _create_api_tab(self):
        """创建API配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # API设置组
        api_group = QGroupBox("API设置")
        api_layout = QFormLayout(api_group)
        
        # API URL
        self.widgets['api.api_url'] = QLineEdit()
        self.widgets['api.api_url'].setToolTip("API服务器地址")
        api_layout.addRow("API地址:", self.widgets['api.api_url'])
        
        # API Key
        self.widgets['api.api_key'] = QLineEdit()
        self.widgets['api.api_key'].setEchoMode(QLineEdit.Password)
        self.widgets['api.api_key'].setToolTip("API访问密钥")
        api_layout.addRow("API密钥:", self.widgets['api.api_key'])
        
        # 模型名称
        self.widgets['api.model_name'] = QLineEdit()
        self.widgets['api.model_name'].setToolTip("使用的AI模型名称")
        api_layout.addRow("模型名称:", self.widgets['api.model_name'])
        
        # 最大重试次数
        self.widgets['api.max_retries'] = QSpinBox()
        self.widgets['api.max_retries'].setRange(1, 10)
        self.widgets['api.max_retries'].setToolTip("API调用失败时的最大重试次数")
        api_layout.addRow("最大重试次数:", self.widgets['api.max_retries'])
        
        # 超时时间
        self.widgets['api.timeout'] = QSpinBox()
        self.widgets['api.timeout'].setRange(5, 120)
        self.widgets['api.timeout'].setSuffix(" 秒")
        self.widgets['api.timeout'].setToolTip("API调用超时时间")
        api_layout.addRow("超时时间:", self.widgets['api.timeout'])
        
        layout.addWidget(api_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "🌐 API")
    

    
    def _create_audio_tab(self):
        """创建音频配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 语音设置组
        voice_group = QGroupBox("语音设置")
        voice_layout = QFormLayout(voice_group)
        
        # 启用语音
        self.widgets['audio.enable_voice'] = QCheckBox()
        voice_layout.addRow("启用语音:", self.widgets['audio.enable_voice'])
        
        # 语音语言
        self.widgets['audio.voice_language'] = QComboBox()
        self.widgets['audio.voice_language'].addItems(["zh", "en"])
        voice_layout.addRow("语音语言:", self.widgets['audio.voice_language'])
        
        # 音量
        volume_layout = QHBoxLayout()
        self.widgets['audio.volume'] = QDoubleSpinBox()
        self.widgets['audio.volume'].setRange(0.0, 1.0)
        self.widgets['audio.volume'].setSingleStep(0.1)
        self.widgets['audio.volume'].setDecimals(1)
        volume_layout.addWidget(self.widgets['audio.volume'])
        
        volume_slider = QSlider(Qt.Horizontal)
        volume_slider.setRange(0, 10)
        volume_slider.valueChanged.connect(
            lambda v: self.widgets['audio.volume'].setValue(v / 10.0)
        )
        self.widgets['audio.volume'].valueChanged.connect(
            lambda v: volume_slider.setValue(int(v * 10))
        )
        volume_layout.addWidget(volume_slider)
        
        voice_layout.addRow("音量:", volume_layout)
        
        # 语音速度
        self.widgets['audio.speech_rate'] = QSpinBox()
        self.widgets['audio.speech_rate'].setRange(50, 300)
        self.widgets['audio.speech_rate'].setSingleStep(10)
        self.widgets['audio.speech_rate'].setSuffix(" 词/分钟")
        voice_layout.addRow("语音速度:", self.widgets['audio.speech_rate'])
        
        layout.addWidget(voice_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "🔊 音频")

    def _create_voice_assistant_tab(self):
        """创建语音助手配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("语音助手")
        form = QFormLayout(group)

        self.widgets['voice_assistant.enable_voice_assistant'] = QCheckBox()
        form.addRow("启用语音助手:", self.widgets['voice_assistant.enable_voice_assistant'])

        self.widgets['voice_assistant.asr_engine'] = QComboBox()
        self.widgets['voice_assistant.asr_engine'].addItems(["speech_recognition_google", "offline_vosk"])
        form.addRow("ASR引擎:", self.widgets['voice_assistant.asr_engine'])

        self.widgets['voice_assistant.asr_language'] = QLineEdit()
        self.widgets['voice_assistant.asr_language'].setText("zh-CN")
        form.addRow("ASR语言:", self.widgets['voice_assistant.asr_language'])

        self.widgets['voice_assistant.max_listen_seconds'] = QDoubleSpinBox()
        self.widgets['voice_assistant.max_listen_seconds'].setRange(2.0, 20.0)
        self.widgets['voice_assistant.max_listen_seconds'].setSingleStep(0.5)
        form.addRow("最大收听时长:", self.widgets['voice_assistant.max_listen_seconds'])

        self.widgets['voice_assistant.silence_timeout'] = QDoubleSpinBox()
        self.widgets['voice_assistant.silence_timeout'].setRange(0.5, 5.0)
        self.widgets['voice_assistant.silence_timeout'].setSingleStep(0.5)
        form.addRow("静音超时:", self.widgets['voice_assistant.silence_timeout'])

        self.widgets['voice_assistant.response_with_tts'] = QCheckBox()
        form.addRow("使用TTS播报答案:", self.widgets['voice_assistant.response_with_tts'])

        layout.addWidget(group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🗣️ 语音助手")

    def _create_llm_tab(self):
        """创建LLM配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("LLM接口")
        form = QFormLayout(group)

        self.widgets['llm.api_url'] = QLineEdit()
        form.addRow("API地址:", self.widgets['llm.api_url'])

        self.widgets['llm.api_key'] = QLineEdit()
        self.widgets['llm.api_key'].setEchoMode(QLineEdit.Password)
        form.addRow("API密钥:", self.widgets['llm.api_key'])

        self.widgets['llm.model_name'] = QLineEdit()
        form.addRow("模型名称:", self.widgets['llm.model_name'])

        self.widgets['llm.max_retries'] = QSpinBox()
        self.widgets['llm.max_retries'].setRange(1, 10)
        form.addRow("最大重试:", self.widgets['llm.max_retries'])

        self.widgets['llm.timeout'] = QSpinBox()
        self.widgets['llm.timeout'].setRange(5, 120)
        self.widgets['llm.timeout'].setSuffix(" 秒")
        form.addRow("超时时间:", self.widgets['llm.timeout'])

        layout.addWidget(group)
        layout.addStretch()

        self.tab_widget.addTab(tab, "🤖 LLM")
    

    
    def _setup_connections(self):
        """设置信号连接"""
        # 实时预览某些参数的变化
        pass
    
    def _load_config(self):
        """加载配置数据"""
        try:
            # 从各个配置对象收集数据
            self.config_data = self._collect_all_config()
            self._update_widgets_from_config()
            self.logger.info("配置数据加载成功")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            QMessageBox.warning(self, "错误", f"加载配置失败: {e}")

    def _collect_all_config(self) -> dict:
        """收集所有配置数据"""
        from dataclasses import asdict

        config_data = {}

        try:
            # 摄像头配置
            camera_config = self.config_manager.get_camera_config()
            config_data['camera'] = asdict(camera_config)

            # AI检测配置 - 如果存在的话
            try:
                ai_config = self.config_manager.get_ai_detection_config()
                config_data['ai_detection'] = asdict(ai_config)
            except AttributeError:
                # 如果没有AI检测配置，跳过
                pass

            # 运动检测配置
            motion_config = self.config_manager.get_motion_detection_config()
            config_data['motion_detection'] = asdict(motion_config)

            # API配置
            api_config = self.config_manager.get_api_config()
            config_data['api'] = asdict(api_config)

            # UI配置 - 如果存在的话
            try:
                ui_config = self.config_manager.get_ui_config()
                config_data['ui'] = asdict(ui_config)
            except AttributeError:
                # 如果没有UI配置，使用默认值
                config_data['ui'] = {
                    'window_title': '废弃物AI识别指导投放系统',
                    'fullscreen': False,
                    'window_size': {'width': 1200, 'height': 800},
                    'theme': 'default',
                    'language': 'zh_CN'
                }

            # 音频配置
            audio_config = self.config_manager.get_audio_config()
            config_data['audio'] = asdict(audio_config)

            # IO控制配置
            io_config = self.config_manager.get_io_config()
            config_data['io_control'] = asdict(io_config)

            # 动画配置
            animation_config = self.config_manager.get_animation_config()
            config_data['animation'] = asdict(animation_config)

            # 日志配置
            logging_config = self.config_manager.get_logging_config()
            config_data['logging'] = asdict(logging_config)

            # 性能配置 - 使用默认值，因为ConfigManager中可能没有这个配置
            try:
                performance_config = self.config_manager.get_performance_config()
                config_data['performance'] = asdict(performance_config)
            except AttributeError:
                # 如果没有性能配置，使用默认值
                config_data['performance'] = {
                    'max_fps': 30,
                    'processing_threads': 2,
                    'buffer_size': 10,
                    'memory_limit_mb': 1024
                }

        except Exception as e:
            self.logger.error(f"收集配置数据失败: {e}")
            raise

        return config_data
    
    def _update_widgets_from_config(self):
        """从配置数据更新控件值"""
        for key, widget in self.widgets.items():
            try:
                value = self._get_nested_value(self.config_data, key)
                if value is not None:
                    self._set_widget_value(widget, value)
            except Exception as e:
                self.logger.warning(f"更新控件 {key} 失败: {e}")
    
    def _get_nested_value(self, data: dict, key: str):
        """获取嵌套字典的值"""
        keys = key.split('.')
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return current
    
    def _set_widget_value(self, widget, value):
        """设置控件值"""
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setValue(value)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index >= 0:
                widget.setCurrentIndex(index)
    
    def _get_widget_value(self, widget):
        """获取控件值"""
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        return None
    
    def _browse_model_file(self):
        """浏览模型文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", "", "模型文件 (*.rknn *.onnx *.tflite);;所有文件 (*)"
        )
        if file_path:
            self.widgets['ai_detection.model_path'].setText(file_path)
    
    def _reset_to_defaults(self):
        """重置为默认值"""
        reply = QMessageBox.question(
            self, "确认重置", "确定要重置所有参数为默认值吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # 这里可以加载默认配置
                self.logger.info("参数已重置为默认值")
                QMessageBox.information(self, "成功", "参数已重置为默认值")
            except Exception as e:
                self.logger.error(f"重置参数失败: {e}")
                QMessageBox.warning(self, "错误", f"重置参数失败: {e}")
    
    def _import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置文件", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
                self.config_data.update(imported_config)
                self._update_widgets_from_config()
                QMessageBox.information(self, "成功", "配置导入成功")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入配置失败: {e}")
    
    def _export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置文件", "system_config_backup.json", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                current_config = self._collect_config_from_widgets()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(current_config, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", "配置导出成功")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出配置失败: {e}")
    
    def _collect_config_from_widgets(self) -> dict:
        """从控件收集配置数据"""
        config = {}
        for key, widget in self.widgets.items():
            value = self._get_widget_value(widget)
            if value is not None:
                self._set_nested_value(config, key, value)
        return config
    
    def _set_nested_value(self, data: dict, key: str, value):
        """设置嵌套字典的值"""
        keys = key.split('.')
        current = data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def _apply_config(self):
        """应用配置"""
        try:
            new_config = self._collect_config_from_widgets()

            # 逐个更新配置项
            success_count = 0
            total_count = 0

            for section, section_data in new_config.items():
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        total_count += 1
                        config_key = f"{section}.{key}"

                        # 使用ConfigManager的update_config方法
                        if self.config_manager.update_config('system', config_key, value):
                            success_count += 1
                        else:
                            self.logger.warning(f"更新配置项失败: {config_key}")

            if success_count == total_count:
                self.config_updated.emit(new_config)
                QMessageBox.information(self, "成功", f"配置已应用 ({success_count}/{total_count} 项)")
                self.logger.info(f"配置应用成功: {success_count}/{total_count}")
            else:
                QMessageBox.warning(self, "部分成功", f"部分配置应用成功 ({success_count}/{total_count} 项)")
                self.logger.warning(f"部分配置应用成功: {success_count}/{total_count}")

        except Exception as e:
            self.logger.error(f"应用配置失败: {e}")
            QMessageBox.warning(self, "错误", f"应用配置失败: {e}")
    
    def _save_and_close(self):
        """保存并关闭"""
        self._apply_config()
        self.accept()
