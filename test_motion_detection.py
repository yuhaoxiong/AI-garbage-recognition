#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运动检测测试界面 - 废弃物AI识别指导投放系统
实时显示运动检测流程的各个阶段，用于调试和参数优化
"""

import sys
import cv2
import numpy as np
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QSpinBox, QCheckBox, QPushButton, QGroupBox,
    QGridLayout, QTextEdit, QSplitter, QTabWidget, QProgressBar,
    QFrame, QScrollArea
)
from PySide6.QtCore import QThread, Signal, QTimer, Qt, QMutex, QMutexLocker
from PySide6.QtGui import QImage, QPixmap, QFont

from utils.config_manager import get_config_manager


class MotionDetectionTester:
    """运动检测测试器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.back_sub = None
        self.last_frame = None
        self.detection_count = 0
        self.last_detection_time = 0
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'motion_frames': 0,
            'detection_count': 0,
            'false_positives': 0,
            'avg_contour_area': 0,
            'max_contour_area': 0
        }
        
        self._initialize_background_subtractor()
    
    def _initialize_background_subtractor(self):
        """初始化背景减除器"""
        history = self.config.get('history', 500)
        dist2_threshold = self.config.get('dist2_threshold', 400.0)
        detect_shadows = self.config.get('detect_shadows', True)
        
        self.back_sub = cv2.createBackgroundSubtractorKNN(
            history=history,
            dist2Threshold=dist2_threshold,
            detectShadows=detect_shadows
        )
        logging.info("背景减除器初始化成功")
    
    def reset_background(self):
        """重置背景减除器"""
        self._initialize_background_subtractor()
        self.stats = {key: 0 for key in self.stats}
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """处理帧并返回所有中间结果"""
        self.stats['total_frames'] += 1
        current_time = time.time()
        
        # 1. 应用背景减除器
        fg_mask = self.back_sub.apply(frame)
        
        # 2. 高斯模糊减少噪声
        blur_kernel = self.config.get('blur_kernel_size', 5)
        blurred = cv2.GaussianBlur(fg_mask, (blur_kernel, blur_kernel), 0)
        
        # 3. 二值化处理
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
        
        # 4. 形态学操作
        kernel_size = self.config.get('kernel_size', 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 5. 查找轮廓
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 6. 分析轮廓
        valid_contours = []
        total_area = 0
        motion_detected = False
        
        detection_cooldown = self.config.get('detection_cooldown', 3.0)
        min_contour_area = self.config.get('min_contour_area', 1000)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            total_area += area
            
            if area >= min_contour_area:
                valid_contours.append(contour)
                
                # 检查冷却时间
                if current_time - self.last_detection_time >= detection_cooldown:
                    motion_detected = True
                    self.last_detection_time = current_time
                    self.stats['detection_count'] += 1
        
        # 7. 绘制结果帧
        result_frame = frame.copy()
        
        # 绘制所有轮廓（灰色）
        cv2.drawContours(result_frame, contours, -1, (128, 128, 128), 1)
        
        # 绘制有效轮廓（绿色）
        cv2.drawContours(result_frame, valid_contours, -1, (0, 255, 0), 2)
        
        # 如果检测到运动，绘制红色边框
        if motion_detected:
            cv2.rectangle(result_frame, (10, 10), (frame.shape[1]-10, frame.shape[0]-10), (0, 0, 255), 3)
            cv2.putText(result_frame, "MOTION DETECTED!", (20, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # 更新统计信息
        if len(contours) > 0:
            self.stats['motion_frames'] += 1
            areas = [cv2.contourArea(c) for c in contours]
            self.stats['avg_contour_area'] = sum(areas) / len(areas)
            self.stats['max_contour_area'] = max(self.stats['max_contour_area'], max(areas))
        
        return {
            'original': frame,
            'fg_mask': fg_mask,
            'blurred': blurred,
            'thresh': thresh,
            'cleaned': cleaned,
            'result': result_frame,
            'contours': contours,
            'valid_contours': valid_contours,
            'motion_detected': motion_detected,
            'total_area': total_area,
            'contour_count': len(contours),
            'valid_contour_count': len(valid_contours)
        }


class CameraWorker(QThread):
    """摄像头工作线程"""
    
    frame_ready = Signal(np.ndarray)
    error_occurred = Signal(str)
    
    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.is_running = False
        self.cap = None
    
    def run(self):
        """运行摄像头捕获循环"""
        try:
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                self.error_occurred.emit(f"无法打开摄像头 {self.camera_id}")
                return
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_running = True
            
            while self.is_running:
                ret, frame = self.cap.read()
                if ret:
                    self.frame_ready.emit(frame)
                else:
                    self.error_occurred.emit("读取摄像头帧失败")
                    break
                
                time.sleep(0.033)  # ~30 FPS
        
        except Exception as e:
            self.error_occurred.emit(f"摄像头工作线程异常: {e}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        """停止摄像头"""
        self.is_running = False
        self.wait()


class MotionDetectionTestWindow(QMainWindow):
    """运动检测测试主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("运动检测测试界面")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化组件
        self.config_manager = get_config_manager()
        self.motion_config = self.config_manager.get_motion_detection_config()
        self.motion_tester = MotionDetectionTester(self.motion_config.__dict__)
        
        # 摄像头工作线程
        self.camera_worker = CameraWorker()
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.camera_worker.error_occurred.connect(self._on_camera_error)
        
        # 状态变量
        self.current_frame_data = None
        self.is_paused = False
        
        # 设置UI
        self._setup_ui()
        self._setup_connections()
        
        # 启动摄像头
        self.camera_worker.start()
        
        # 状态更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(1000)  # 每秒更新一次统计
    
    def _setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：视频显示区域
        video_widget = self._create_video_widget()
        splitter.addWidget(video_widget)
        
        # 右侧：控制和统计区域
        control_widget = self._create_control_widget()
        splitter.addWidget(control_widget)
        
        # 设置分割器比例
        splitter.setSizes([1000, 400])
    
    def _create_video_widget(self) -> QWidget:
        """创建视频显示区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 原始画面
        self.original_label = QLabel()
        self.original_label.setMinimumSize(320, 240)
        self.original_label.setStyleSheet("border: 1px solid gray")
        self.original_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.original_label, "原始画面")
        
        # 前景掩码
        self.fg_mask_label = QLabel()
        self.fg_mask_label.setMinimumSize(320, 240)
        self.fg_mask_label.setStyleSheet("border: 1px solid gray")
        self.fg_mask_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.fg_mask_label, "前景掩码")
        
        # 模糊处理
        self.blurred_label = QLabel()
        self.blurred_label.setMinimumSize(320, 240)
        self.blurred_label.setStyleSheet("border: 1px solid gray")
        self.blurred_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.blurred_label, "模糊处理")
        
        # 二值化
        self.thresh_label = QLabel()
        self.thresh_label.setMinimumSize(320, 240)
        self.thresh_label.setStyleSheet("border: 1px solid gray")
        self.thresh_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.thresh_label, "二值化")
        
        # 形态学处理
        self.cleaned_label = QLabel()
        self.cleaned_label.setMinimumSize(320, 240)
        self.cleaned_label.setStyleSheet("border: 1px solid gray")
        self.cleaned_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.cleaned_label, "形态学处理")
        
        # 检测结果
        self.result_label = QLabel()
        self.result_label.setMinimumSize(320, 240)
        self.result_label.setStyleSheet("border: 1px solid gray")
        self.result_label.setAlignment(Qt.AlignCenter)
        tab_widget.addTab(self.result_label, "检测结果")
        
        return widget
    
    def _create_control_widget(self) -> QWidget:
        """创建控制区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 控制按钮
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout(control_group)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self._toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("重置背景")
        self.reset_btn.clicked.connect(self._reset_background)
        control_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("保存当前帧")
        self.save_btn.clicked.connect(self._save_current_frame)
        control_layout.addWidget(self.save_btn)
        
        layout.addWidget(control_group)
        
        # 参数调节
        params_group = QGroupBox("参数调节")
        params_layout = QGridLayout(params_group)
        
        # 运动阈值
        params_layout.addWidget(QLabel("运动阈值:"), 0, 0)
        self.motion_threshold_slider = QSlider(Qt.Horizontal)
        self.motion_threshold_slider.setRange(100, 2000)
        self.motion_threshold_slider.setValue(self.motion_config.motion_threshold)
        self.motion_threshold_slider.valueChanged.connect(self._update_motion_threshold)
        params_layout.addWidget(self.motion_threshold_slider, 0, 1)
        self.motion_threshold_label = QLabel(str(self.motion_config.motion_threshold))
        params_layout.addWidget(self.motion_threshold_label, 0, 2)
        
        # 最小轮廓面积
        params_layout.addWidget(QLabel("最小轮廓面积:"), 1, 0)
        self.min_area_slider = QSlider(Qt.Horizontal)
        self.min_area_slider.setRange(100, 5000)
        self.min_area_slider.setValue(self.motion_config.min_contour_area)
        self.min_area_slider.valueChanged.connect(self._update_min_area)
        params_layout.addWidget(self.min_area_slider, 1, 1)
        self.min_area_label = QLabel(str(self.motion_config.min_contour_area))
        params_layout.addWidget(self.min_area_label, 1, 2)
        
        # 检测冷却时间
        params_layout.addWidget(QLabel("冷却时间(秒):"), 2, 0)
        self.cooldown_slider = QSlider(Qt.Horizontal)
        self.cooldown_slider.setRange(1, 10)
        self.cooldown_slider.setValue(int(self.motion_config.detection_cooldown))
        self.cooldown_slider.valueChanged.connect(self._update_cooldown)
        params_layout.addWidget(self.cooldown_slider, 2, 1)
        self.cooldown_label = QLabel(str(self.motion_config.detection_cooldown))
        params_layout.addWidget(self.cooldown_label, 2, 2)
        
        # 模糊核大小
        params_layout.addWidget(QLabel("模糊核大小:"), 3, 0)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(3, 21)
        self.blur_slider.setValue(self.motion_config.blur_kernel_size)
        self.blur_slider.valueChanged.connect(self._update_blur_size)
        params_layout.addWidget(self.blur_slider, 3, 1)
        self.blur_label = QLabel(str(self.motion_config.blur_kernel_size))
        params_layout.addWidget(self.blur_label, 3, 2)
        
        layout.addWidget(params_group)
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        layout.addWidget(stats_group)
        
        # 实时信息
        info_group = QGroupBox("实时信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(info_group)
        
        return widget
    
    def _setup_connections(self):
        """设置信号连接"""
        pass
    
    def _on_frame_ready(self, frame: np.ndarray):
        """处理新帧"""
        if self.is_paused:
            return
        
        # 处理帧
        self.current_frame_data = self.motion_tester.process_frame(frame)
        
        # 更新显示
        self._update_displays()
        self._update_info()
    
    def _update_displays(self):
        """更新所有显示"""
        if not self.current_frame_data:
            return
        
        data = self.current_frame_data
        
        # 更新各个标签
        self._update_label(self.original_label, data['original'])
        self._update_label(self.fg_mask_label, data['fg_mask'])
        self._update_label(self.blurred_label, data['blurred'])
        self._update_label(self.thresh_label, data['thresh'])
        self._update_label(self.cleaned_label, data['cleaned'])
        self._update_label(self.result_label, data['result'])
    
    def _update_label(self, label: QLabel, image: np.ndarray):
        """更新标签显示"""
        if len(image.shape) == 3:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        else:
            height, width = image.shape
            bytes_per_line = width
            q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
    
    def _update_info(self):
        """更新实时信息"""
        if not self.current_frame_data:
            return
        
        data = self.current_frame_data
        
        info_text = f"""当前帧信息:
运动检测: {'是' if data['motion_detected'] else '否'}
轮廓数量: {data['contour_count']}
有效轮廓: {data['valid_contour_count']}
总面积: {data['total_area']:.0f}
时间: {datetime.now().strftime('%H:%M:%S')}
"""
        
        self.info_text.setPlainText(info_text)
    
    def _update_stats(self):
        """更新统计信息"""
        stats = self.motion_tester.stats
        
        motion_rate = (stats['motion_frames'] / max(stats['total_frames'], 1)) * 100
        detection_rate = (stats['detection_count'] / max(stats['total_frames'], 1)) * 100
        
        stats_text = f"""统计信息:
总帧数: {stats['total_frames']}
运动帧数: {stats['motion_frames']} ({motion_rate:.1f}%)
检测次数: {stats['detection_count']} ({detection_rate:.1f}%)
平均轮廓面积: {stats['avg_contour_area']:.0f}
最大轮廓面积: {stats['max_contour_area']:.0f}
运行时间: {int(stats['total_frames'] / 30 / 60)}:{int((stats['total_frames'] / 30) % 60):02d}
"""
        
        self.stats_text.setPlainText(stats_text)
    
    def _toggle_pause(self):
        """切换暂停状态"""
        self.is_paused = not self.is_paused
        self.pause_btn.setText("继续" if self.is_paused else "暂停")
    
    def _reset_background(self):
        """重置背景"""
        self.motion_tester.reset_background()
        self._update_stats()
    
    def _save_current_frame(self):
        """保存当前帧"""
        if not self.current_frame_data:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存各个处理阶段的图像
        stages = ['original', 'fg_mask', 'blurred', 'thresh', 'cleaned', 'result']
        for stage in stages:
            if stage in self.current_frame_data:
                filename = f"test_motion_{stage}_{timestamp}.jpg"
                cv2.imwrite(filename, self.current_frame_data[stage])
        
        logging.info(f"已保存测试帧: {timestamp}")
    
    def _update_motion_threshold(self, value):
        """更新运动阈值"""
        self.motion_tester.config['motion_threshold'] = value
        self.motion_threshold_label.setText(str(value))
    
    def _update_min_area(self, value):
        """更新最小轮廓面积"""
        self.motion_tester.config['min_contour_area'] = value
        self.min_area_label.setText(str(value))
    
    def _update_cooldown(self, value):
        """更新冷却时间"""
        self.motion_tester.config['detection_cooldown'] = float(value)
        self.cooldown_label.setText(str(value))
    
    def _update_blur_size(self, value):
        """更新模糊核大小"""
        # 确保是奇数
        if value % 2 == 0:
            value += 1
        self.motion_tester.config['blur_kernel_size'] = value
        self.blur_label.setText(str(value))
    
    def _on_camera_error(self, error: str):
        """处理摄像头错误"""
        logging.error(f"摄像头错误: {error}")
        self.info_text.setPlainText(f"摄像头错误: {error}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.camera_worker.stop()
        self.stats_timer.stop()
        event.accept()


def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MotionDetectionTestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 