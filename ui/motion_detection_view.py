from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap, QFont
import cv2
import numpy as np

class MotionDetectionView(QWidget):
    def __init__(self, motion_worker, parent=None):
        super().__init__(parent)
        self.motion_worker = motion_worker
        self.setWindowTitle("运动检测实时监控")
        self.resize(900, 700)

        self.image_label = QLabel("等待视频流...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.status_label = QLabel("状态：未检测")
        self.status_label.setAlignment(Qt.AlignCenter)
        # 使用点字号替代 px
        self.status_label.setFont(QFont("Microsoft YaHei", 12))
        self.status_label.setStyleSheet("color:#333;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(self.status_label)

        # 定时刷新画面
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        # 绑定运动检测信号
        self.motion_worker.motion_detected.connect(self.on_motion_detected)
        self.motion_worker.detection_completed.connect(self.on_detection_completed)
        self.motion_worker.error_occurred.connect(self.on_error)

    def update_frame(self):
        # 获取当前帧
        if hasattr(self.motion_worker, "camera_worker") and self.motion_worker.camera_worker:
            frame = self.motion_worker.camera_worker.get_current_frame()
            if frame is not None:
                display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = display.shape
                bytes_per_line = ch * w
                qimg = QImage(display.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.image_label.setPixmap(QPixmap.fromImage(qimg).scaled(
                    self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio))
            else:
                self.image_label.setText("无视频信号")
        else:
            self.image_label.setText("未连接摄像头")

    def on_motion_detected(self):
        self.status_label.setText("状态：检测到运动")
        self.status_label.setStyleSheet("font-size:18px; color:#e74c3c;")

    def on_detection_completed(self, result):
        self.status_label.setText("状态：运动检测完成")
        self.status_label.setStyleSheet("font-size:18px; color:#27ae60;")

    def on_error(self, msg):
        self.status_label.setText(f"错误：{msg}")
        self.status_label.setStyleSheet("font-size:18px; color:#e67e22;") 