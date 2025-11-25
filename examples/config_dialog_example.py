#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数配置界面使用示例
演示如何在应用程序中集成和使用参数配置界面
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PySide6.QtCore import Qt, Slot

# 导入项目模块
from ui.config_dialog import ConfigDialog
from utils.config_manager import get_config_manager


class ConfigExampleWindow(QMainWindow):
    """配置示例窗口"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = get_config_manager()
        
        self.setWindowTitle("参数配置界面使用示例")
        self.setGeometry(300, 300, 600, 500)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title_label = QLabel("参数配置界面集成示例")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 说明
        info_label = QLabel("""
本示例演示如何在应用程序中集成参数配置界面：

1. 导入 ConfigDialog 类
2. 创建配置对话框实例
3. 连接配置更新信号
4. 处理配置变更
        """)
        info_label.setStyleSheet("padding: 15px; background-color: #f0f8ff; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # 当前配置显示
        self.config_display = QTextEdit()
        self.config_display.setMaximumHeight(200)
        self.config_display.setStyleSheet("font-family: monospace; font-size: 10px;")
        layout.addWidget(QLabel("当前配置:"))
        layout.addWidget(self.config_display)
        
        # 按钮
        self.config_button = QPushButton("打开参数配置")
        self.config_button.setStyleSheet("font-size: 14px; padding: 10px;")
        self.config_button.clicked.connect(self._open_config_dialog)
        layout.addWidget(self.config_button)
        
        self.refresh_button = QPushButton("刷新配置显示")
        self.refresh_button.clicked.connect(self._refresh_config_display)
        layout.addWidget(self.refresh_button)
        
        # 初始显示配置
        self._refresh_config_display()
    
    def _open_config_dialog(self):
        """打开配置对话框"""
        try:
            # 创建配置对话框
            config_dialog = ConfigDialog(self)
            
            # 连接配置更新信号
            config_dialog.config_updated.connect(self._on_config_updated)
            
            # 显示对话框
            result = config_dialog.exec()
            
            if result == ConfigDialog.Accepted:
                print("✅ 配置对话框已确认")
            else:
                print("❌ 配置对话框已取消")
                
        except Exception as e:
            print(f"❌ 打开配置对话框失败: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot(dict)
    def _on_config_updated(self, config):
        """配置更新回调"""
        print("📝 配置已更新")
        print(f"配置项数量: {len(config) if isinstance(config, dict) else 'N/A'}")
        
        # 刷新配置显示
        self._refresh_config_display()
        
        # 这里可以添加配置变更后的处理逻辑
        # 例如：重新初始化相关组件、更新UI等
        self._handle_config_changes(config)
    
    def _refresh_config_display(self):
        """刷新配置显示"""
        try:
            config = self.config_manager.get_all_config()
            
            # 格式化显示配置
            config_text = self._format_config_for_display(config)
            self.config_display.setPlainText(config_text)
            
        except Exception as e:
            self.config_display.setPlainText(f"获取配置失败: {e}")
    
    def _format_config_for_display(self, config, indent=0):
        """格式化配置用于显示"""
        lines = []
        prefix = "  " * indent
        
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, dict):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_config_for_display(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        else:
            lines.append(f"{prefix}{config}")
        
        return "\n".join(lines)
    
    def _handle_config_changes(self, config):
        """处理配置变更"""
        # 示例：检查特定配置项的变更
        
        # 检查摄像头配置
        if 'camera' in config:
            camera_config = config['camera']
            print(f"📷 摄像头配置更新:")
            print(f"   设备ID: {camera_config.get('device_id', 'N/A')}")
            print(f"   分辨率: {camera_config.get('resolution', 'N/A')}")
            print(f"   帧率: {camera_config.get('fps', 'N/A')}")
        
        # 检查AI检测配置
        if 'ai_detection' in config:
            ai_config = config['ai_detection']
            print(f"🤖 AI检测配置更新:")
            print(f"   置信度阈值: {ai_config.get('confidence_threshold', 'N/A')}")
            print(f"   模型路径: {ai_config.get('model_path', 'N/A')}")
        
        # 检查界面配置
        if 'ui' in config:
            ui_config = config['ui']
            print(f"🎨 界面配置更新:")
            print(f"   主题: {ui_config.get('theme', 'N/A')}")
            print(f"   语言: {ui_config.get('language', 'N/A')}")
        
        # 检查音频配置
        if 'audio' in config:
            audio_config = config['audio']
            print(f"🔊 音频配置更新:")
            print(f"   启用语音: {audio_config.get('enable_voice', 'N/A')}")
            print(f"   音量: {audio_config.get('volume', 'N/A')}")
        
        # 在实际应用中，这里可以：
        # 1. 重新初始化摄像头（如果设备ID或分辨率改变）
        # 2. 重新加载AI模型（如果模型路径改变）
        # 3. 更新界面主题（如果主题改变）
        # 4. 调整语音设置（如果音频配置改变）
        # 5. 重启相关服务或组件


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    try:
        # 创建示例窗口
        example_window = ConfigExampleWindow()
        example_window.show()
        
        print("🔧 参数配置界面集成示例已启动")
        print("📋 点击按钮体验配置界面功能")
        
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
