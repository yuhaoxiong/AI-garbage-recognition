#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃物AI识别指导投放系统 - 主程序入口
基于PySide6和AI技术的智能垃圾分类指导系统
"""

import sys
import os
import logging
import traceback
import time
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入错误恢复机制
try:
    from utils.error_recovery import get_recovery_manager, with_error_recovery, safe_execute
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    logging.warning("错误恢复模块不可用")

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont

# 安全导入关键模块
try:
    from ui.main_window import MainWindow
    MAIN_WINDOW_AVAILABLE = True
except ImportError as e:
    MAIN_WINDOW_AVAILABLE = False
    logging.error(f"主窗口模块导入失败: {e}")

try:
    from utils.config_manager import get_config_manager
    CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    CONFIG_MANAGER_AVAILABLE = False
    logging.error(f"配置管理器导入失败: {e}")


@with_error_recovery("日志系统初始化")
def setup_logging():
    """设置日志系统"""
    try:
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 配置日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 创建格式化器
        formatter = logging.Formatter(log_format)
        
        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器
        try:
            file_handler = logging.FileHandler(
                log_dir / "waste_detection.log", 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # 如果无法创建文件处理器，只使用控制台
            logging.warning(f"无法创建文件日志处理器: {e}")
        
        logging.info("日志系统初始化成功")
        
    except Exception as e:
        print(f"日志系统初始化失败: {e}")
        # 至少确保基本的控制台日志可用
        logging.basicConfig(level=logging.INFO, format=log_format)


@with_error_recovery("依赖检查")
def check_dependencies():
    """检查依赖库"""
    missing_deps = []
    optional_deps = []
    
    # 检查必需依赖
    required_deps = [
        ("cv2", "opencv-python"),
        ("numpy", "numpy"),
        ("PySide6.QtWidgets", "PySide6")
    ]
    
    for module, package in required_deps:
        try:
            __import__(module)
        except ImportError:
            missing_deps.append(package)
    
    # 检查可选依赖
    optional_deps_list = [
        ("pyttsx3", "pyttsx3 (语音功能)"),
        ("pygame", "pygame (音频播放)"),
        ("rknnlite.api", "rknnlite (RKNN推理)"),
        ("RPi.GPIO", "RPi.GPIO (GPIO控制)")
    ]
    
    for module, description in optional_deps_list:
        try:
            __import__(module)
        except ImportError:
            optional_deps.append(description)
    
    if missing_deps:
        error_msg = f"缺少必需依赖库: {', '.join(missing_deps)}\n"
        error_msg += "请使用以下命令安装:\n"
        error_msg += f"pip install {' '.join(missing_deps)}"
        return False, error_msg
    
    if optional_deps:
        warning_msg = f"缺少可选依赖库: {', '.join(optional_deps)}\n"
        warning_msg += "某些功能可能受限，但系统仍可正常运行。"
        logging.warning(warning_msg)
    
    return True, None


def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理器"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.critical(f"未捕获的异常: {error_msg}")
    
    # 使用错误恢复机制
    if ERROR_RECOVERY_AVAILABLE:
        recovery_manager = get_recovery_manager()
        try:
            recovery_manager.handle_error(exc_value, "全局异常处理")
        except Exception as recovery_error:
            logging.error(f"错误恢复失败: {recovery_error}")
    
    # 显示错误对话框
    if QApplication.instance():
        try:
            QMessageBox.critical(
                None, 
                "系统错误", 
                f"系统遇到严重错误:\n\n{exc_value}\n\n详细信息请查看日志文件。"
            )
        except Exception:
            # 如果无法显示对话框，至少打印错误
            print(f"严重错误: {exc_value}")


@with_error_recovery("启动画面创建")
def create_splash_screen():
    """创建启动画面"""
    try:
        # 创建简单的启动画面
        splash = QSplashScreen()
        splash.setFixedSize(400, 300)
        
        # 设置样式
        splash.setStyleSheet("""
            QSplashScreen {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #74b9ff, stop:1 #0984e3);
                border-radius: 15px;
            }
        """)
        
        # 显示文本
        splash.showMessage(
            "废弃物AI识别指导投放系统\n\n正在加载...", 
            Qt.AlignCenter, 
            Qt.white
        )
        
        # 设置字体
        font = QFont("Microsoft YaHei", 14, QFont.Bold)
        splash.setFont(font)
        
        # 确保启动画面在屏幕中央
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            splash_x = (screen_geometry.width() - splash.width()) // 2
            splash_y = (screen_geometry.height() - splash.height()) // 2
            splash.move(splash_x, splash_y)
        
        return splash
        
    except Exception as e:
        logging.error(f"创建启动画面失败: {e}")
        return None


def create_fallback_window():
    """创建备用窗口（当主窗口无法创建时）"""
    try:
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
        
        class FallbackWindow(QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("废弃物AI识别指导投放系统 - 安全模式")
                self.setGeometry(100, 100, 600, 400)
                
                layout = QVBoxLayout()
                
                # 错误信息
                error_label = QLabel(
                    "系统运行在安全模式\n\n"
                    "主要功能可能不可用，但系统仍在运行。\n"
                    "请检查日志文件以获取详细信息。"
                )
                error_label.setAlignment(Qt.AlignCenter)
                error_label.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        color: #e74c3c;
                        padding: 20px;
                        background-color: #f8f9fa;
                        border: 2px solid #e74c3c;
                        border-radius: 10px;
                    }
                """)
                
                # 退出按钮
                exit_button = QPushButton("退出")
                exit_button.clicked.connect(self.close)
                exit_button.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
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
                
                layout.addWidget(error_label)
                layout.addWidget(exit_button)
                self.setLayout(layout)
        
        return FallbackWindow()
        
    except Exception as e:
        logging.error(f"创建备用窗口失败: {e}")
        return None


def main():
    """主函数"""
    start_time = time.time()
    
    try:
        # 设置日志
        setup_logging()
        logging.info("启动废弃物AI识别指导投放系统")
        
        # 初始化错误恢复管理器
        if ERROR_RECOVERY_AVAILABLE:
            recovery_manager = get_recovery_manager()
            logging.info("错误恢复系统已启用")
        
        # 检查依赖
        deps_result = safe_execute(
            lambda: check_dependencies(),
            default_value=(False, "依赖检查失败"),
            context="依赖检查"
        )
        
        if deps_result and not deps_result[0]:
            print(f"依赖检查失败: {deps_result[1]}")
            return 1
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("废弃物AI识别指导投放系统")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("AI智能环保")
        
        # 设置全局异常处理
        sys.excepthook = handle_exception
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        
        # 加载配置
        config_manager = None
        if CONFIG_MANAGER_AVAILABLE:
            config_manager = safe_execute(
                lambda: get_config_manager(),
                default_value=None,
                context="配置管理器初始化"
            )
            if config_manager:
                logging.info("配置管理器加载完成")
            else:
                logging.warning("配置管理器加载失败，使用默认设置")
        
        # 创建启动画面
        splash = create_splash_screen()
        if splash:
            splash.show()
            app.processEvents()
        
        # 显示加载进度
        loading_steps = [
            "初始化组件...",
            "加载配置文件...",
            "启动界面..."
        ]
        
        for i, step in enumerate(loading_steps):
            if splash:
                splash.showMessage(
                    f"废弃物AI识别指导投放系统\n\n{step}", 
                    Qt.AlignCenter, 
                    Qt.white
                )
                app.processEvents()
            
            # 模拟加载时间
            time.sleep(0.5)
        
        # 创建主窗口
        main_window = None
        if MAIN_WINDOW_AVAILABLE:
            main_window = safe_execute(
                lambda: MainWindow(),
                default_value=None,
                context="主窗口创建"
            )
        
        if main_window:
            # 主窗口创建成功
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()
            
            # 处理事件确保窗口正确显示
            app.processEvents()
            
            logging.info("主窗口显示成功")
            
        else:
            # 主窗口创建失败，使用备用窗口
            logging.warning("主窗口创建失败，启动备用窗口")
            fallback_window = create_fallback_window()
            
            if fallback_window:
                fallback_window.show()
                logging.info("备用窗口显示成功")
            else:
                # 连备用窗口都无法创建
                logging.critical("无法创建任何窗口，系统无法启动")
                if splash:
                    splash.close()
                QMessageBox.critical(
                    None,
                    "启动失败",
                    "系统无法启动，请检查安装和配置。"
                )
                return 1
        
        # 关闭启动画面
        if splash:
            splash.close()
        
        # 记录启动时间
        startup_time = time.time() - start_time
        logging.info(f"系统启动完成，耗时: {startup_time:.2f}秒")
        
        # 运行应用程序
        exit_code = app.exec()
        logging.info(f"应用程序退出，退出码: {exit_code}")
        
        # 显示错误恢复摘要
        if ERROR_RECOVERY_AVAILABLE:
            recovery_manager = get_recovery_manager()
            error_summary = recovery_manager.get_error_summary()
            if error_summary["total_errors"] > 0:
                logging.info(f"错误恢复摘要: {error_summary}")
        
        return exit_code
        
    except Exception as e:
        error_msg = f"应用程序启动失败: {e}"
        logging.critical(error_msg)
        print(error_msg)
        
        # 尝试显示错误信息
        try:
            if 'app' in locals():
                QMessageBox.critical(
                    None,
                    "严重错误",
                    f"系统启动过程中发生严重错误:\n\n{e}\n\n请检查日志文件获取详细信息。"
                )
        except Exception:
            pass
        
        return 1


if __name__ == "__main__":
    sys.exit(main()) 