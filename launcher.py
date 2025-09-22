#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃物AI识别指导投放系统 - 启动器
提供用户友好的启动界面和选项选择
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                  QHBoxLayout, QLabel, QPushButton, QGroupBox,
                                  QCheckBox, QComboBox, QTextEdit, QProgressBar,
                                  QMessageBox, QFrame)
    from PySide6.QtCore import Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QFont, QPixmap, QIcon
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("PySide6 不可用，无法启动图形界面")


class SystemChecker(QThread):
    """系统检查线程"""
    
    progress_updated = Signal(int, str)
    check_completed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.checks = [
            ("检查Python版本", self._check_python_version),
            ("检查必需依赖", self._check_required_deps),
            ("检查可选依赖", self._check_optional_deps),
            ("检查配置文件", self._check_config_files),
            ("检查资源文件", self._check_resource_files),
            ("检查权限", self._check_permissions)
        ]
    
    def run(self):
        """运行系统检查"""
        results = {}
        total_checks = len(self.checks)
        
        for i, (name, check_func) in enumerate(self.checks):
            self.progress_updated.emit(int((i / total_checks) * 100), f"正在{name}...")
            
            try:
                result = check_func()
                results[name] = result
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
            
            # 模拟检查时间
            self.msleep(500)
        
        self.progress_updated.emit(100, "检查完成")
        self.check_completed.emit(results)
    
    def _check_python_version(self):
        """检查Python版本"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            return {
                "status": "ok",
                "message": f"Python版本: {version.major}.{version.minor}.{version.micro}"
            }
        else:
            return {
                "status": "warning",
                "message": f"Python版本较低: {version.major}.{version.minor}.{version.micro}，建议3.8+"
            }
    
    def _check_required_deps(self):
        """检查必需依赖"""
        required_deps = [
            ("cv2", "opencv-python"),
            ("numpy", "numpy"),
            ("PySide6", "PySide6")
        ]
        
        missing = []
        for module, package in required_deps:
            try:
                __import__(module)
            except ImportError:
                missing.append(package)
        
        if not missing:
            return {"status": "ok", "message": "所有必需依赖已安装"}
        else:
            return {
                "status": "error",
                "message": f"缺少必需依赖: {', '.join(missing)}"
            }
    
    def _check_optional_deps(self):
        """检查可选依赖"""
        optional_deps = [
            ("pyttsx3", "语音功能"),
            ("pygame", "音频播放"),
            ("rknnlite", "RKNN推理"),
            ("RPi.GPIO", "GPIO控制")
        ]
        
        available = []
        missing = []
        
        for module, description in optional_deps:
            try:
                __import__(module)
                available.append(description)
            except ImportError:
                missing.append(description)
        
        message = f"可用功能: {', '.join(available) if available else '无'}"
        if missing:
            message += f"\n不可用功能: {', '.join(missing)}"
        
        return {"status": "ok", "message": message}
    
    def _check_config_files(self):
        """检查配置文件"""
        config_files = [
            "config/system_config.json",
            "config/waste_classification.json"
        ]
        
        missing = []
        for file_path in config_files:
            if not Path(file_path).exists():
                missing.append(file_path)
        
        if not missing:
            return {"status": "ok", "message": "配置文件完整"}
        else:
            return {
                "status": "warning",
                "message": f"缺少配置文件: {', '.join(missing)}，将使用默认配置"
            }
    
    def _check_resource_files(self):
        """检查资源文件"""
        resource_dirs = ["res", "models", "data", "logs"]
        
        for dir_name in resource_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
        
        return {"status": "ok", "message": "资源目录已准备"}
    
    def _check_permissions(self):
        """检查权限"""
        test_dirs = ["logs", "data", "config"]
        
        for dir_name in test_dirs:
            dir_path = Path(dir_name)
            try:
                # 测试写入权限
                test_file = dir_path / ".permission_test"
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                return {
                    "status": "error",
                    "message": f"缺少 {dir_name} 目录的写入权限"
                }
        
        return {"status": "ok", "message": "权限检查通过"}


class LauncherWindow(QMainWindow):
    """启动器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.system_checker = None
        self.check_results = {}
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("废弃物AI识别指导投放系统 - 启动器")
        self.setFixedSize(800, 600)
        
        # 居中显示
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题
        title_label = QLabel("废弃物AI识别指导投放系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #74b9ff, stop:1 #0984e3);
                border-radius: 10px;
                color: white;
            }
        """)
        
        # 系统检查区域
        check_group = QGroupBox("系统检查")
        check_group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        check_layout = QVBoxLayout(check_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # 状态标签
        self.status_label = QLabel("点击'检查系统'开始系统检查")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 检查结果显示
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(150)
        self.result_text.setVisible(False)
        
        # 检查按钮
        self.check_button = QPushButton("检查系统")
        self.check_button.setFont(QFont("Microsoft YaHei", 12))
        self.check_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        check_layout.addWidget(self.progress_bar)
        check_layout.addWidget(self.status_label)
        check_layout.addWidget(self.result_text)
        check_layout.addWidget(self.check_button)
        
        # 启动选项区域
        options_group = QGroupBox("启动选项")
        options_group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        options_layout = QVBoxLayout(options_group)
        
        # 启动模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("启动模式:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "完整模式 (推荐)",
            "简化模式",
            "调试模式",
            "安全模式"
        ])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        
        # 功能选项
        self.enable_io_check = QCheckBox("启用IO控制")
        self.enable_animation_check = QCheckBox("启用动画效果")
        self.enable_voice_check = QCheckBox("启用语音指导")
        
        self.enable_animation_check.setChecked(True)
        self.enable_voice_check.setChecked(True)
        
        options_layout.addLayout(mode_layout)
        options_layout.addWidget(self.enable_io_check)
        options_layout.addWidget(self.enable_animation_check)
        options_layout.addWidget(self.enable_voice_check)
        
        # 启动按钮区域
        button_layout = QHBoxLayout()
        
        self.launch_button = QPushButton("启动系统")
        self.launch_button.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.launch_button.setStyleSheet("""
            QPushButton {
                padding: 15px 30px;
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        
        self.exit_button = QPushButton("退出")
        self.exit_button.setFont(QFont("Microsoft YaHei", 12))
        self.exit_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.launch_button)
        button_layout.addWidget(self.exit_button)
        
        # 添加到主布局
        main_layout.addWidget(title_label)
        main_layout.addWidget(check_group)
        main_layout.addWidget(options_group)
        main_layout.addLayout(button_layout)
        
        # 设置主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def _setup_connections(self):
        """设置信号连接"""
        self.check_button.clicked.connect(self._start_system_check)
        self.launch_button.clicked.connect(self._launch_system)
        self.exit_button.clicked.connect(self.close)
    
    def _start_system_check(self):
        """开始系统检查"""
        self.check_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_text.setVisible(False)
        
        # 创建并启动检查线程
        self.system_checker = SystemChecker()
        self.system_checker.progress_updated.connect(self._update_progress)
        self.system_checker.check_completed.connect(self._on_check_completed)
        self.system_checker.start()
    
    def _update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def _on_check_completed(self, results: dict):
        """检查完成处理"""
        self.check_results = results
        self.check_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.result_text.setVisible(True)
        
        # 显示检查结果
        result_text = "系统检查结果:\n\n"
        has_errors = False
        
        for check_name, result in results.items():
            status = result.get("status", "unknown")
            message = result.get("message", "无信息")
            
            if status == "ok":
                result_text += f"✅ {check_name}: {message}\n"
            elif status == "warning":
                result_text += f"⚠️ {check_name}: {message}\n"
            elif status == "error":
                result_text += f"❌ {check_name}: {message}\n"
                has_errors = True
            else:
                result_text += f"❓ {check_name}: {message}\n"
        
        self.result_text.setPlainText(result_text)
        
        # 根据检查结果启用/禁用启动按钮
        if has_errors:
            self.launch_button.setEnabled(False)
            self.status_label.setText("系统检查发现错误，无法启动")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self.launch_button.setEnabled(True)
            self.status_label.setText("系统检查通过，可以启动")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
    
    def _launch_system(self):
        """启动系统"""
        try:
            # 根据选择的模式确定启动脚本
            mode = self.mode_combo.currentText()
            
            if "完整模式" in mode:
                script = "main.py"
            elif "简化模式" in mode:
                script = "simple_main.py"
            elif "调试模式" in mode:
                script = "debug_main.py"
            elif "安全模式" in mode:
                script = "main.py"  # 使用主程序的安全模式
            else:
                script = "main.py"
            
            # 设置环境变量
            env = os.environ.copy()
            
            if self.enable_io_check.isChecked():
                env["ENABLE_IO_CONTROL"] = "1"
            
            if self.enable_animation_check.isChecked():
                env["ENABLE_ANIMATIONS"] = "1"
            
            if self.enable_voice_check.isChecked():
                env["ENABLE_VOICE"] = "1"
            
            if "调试模式" in mode:
                env["DEBUG"] = "1"
            
            # 启动系统
            self.launch_button.setEnabled(False)
            self.launch_button.setText("正在启动...")
            
            # 使用subprocess启动主程序
            process = subprocess.Popen(
                [sys.executable, script],
                env=env,
                cwd=project_root
            )
            
            # 延迟关闭启动器
            QTimer.singleShot(2000, self.close)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "启动失败",
                f"无法启动系统:\n{e}"
            )
            self.launch_button.setEnabled(True)
            self.launch_button.setText("启动系统")


def main():
    """主函数"""
    if not PYSIDE6_AVAILABLE:
        print("PySide6 不可用，尝试直接启动系统...")
        try:
            subprocess.run([sys.executable, "main.py"], cwd=project_root)
        except Exception as e:
            print(f"启动失败: {e}")
        return
    
    app = QApplication(sys.argv)
    app.setApplicationName("废弃物AI识别指导投放系统启动器")
    app.setApplicationVersion("1.0.0")
    
    launcher = LauncherWindow()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 