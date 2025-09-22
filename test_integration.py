#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成功能测试脚本 - 废弃物AI识别指导投放系统
验证运动检测测试界面与主程序的集成功能
"""

import sys
import time
import logging
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有必要模块的导入"""
    print("🔍 测试模块导入...")
    
    try:
        from ui.main_window import MainWindow
        print("  ✅ 主窗口模块导入成功")
    except ImportError as e:
        print(f"  ❌ 主窗口模块导入失败: {e}")
        return False
    
    try:
        from ui.motion_detection_test_window import MotionDetectionTestWindow
        print("  ✅ 运动检测测试窗口模块导入成功")
    except ImportError as e:
        print(f"  ❌ 运动检测测试窗口模块导入失败: {e}")
        return False
    
    try:
        from utils.config_manager import get_config_manager
        print("  ✅ 配置管理器导入成功")
    except ImportError as e:
        print(f"  ❌ 配置管理器导入失败: {e}")
        return False
    
    return True

def test_config_manager():
    """测试配置管理器"""
    print("\n⚙️ 测试配置管理器...")
    
    try:
        from utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # 测试运动检测配置
        motion_config = config_manager.get_motion_detection_config()
        print(f"  ✅ 运动检测配置加载成功")
        print(f"    - 运动阈值: {motion_config.motion_threshold}")
        print(f"    - 最小轮廓面积: {motion_config.min_contour_area}")
        print(f"    - 冷却时间: {motion_config.detection_cooldown}秒")
        
        # 测试API配置
        api_config = config_manager.get_api_config()
        print(f"  ✅ API配置加载成功")
        print(f"    - API URL: {api_config.api_url}")
        print(f"    - 模型名称: {api_config.model_name}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 配置管理器测试失败: {e}")
        return False

def test_ui_creation():
    """测试UI创建"""
    print("\n🖥️ 测试UI组件创建...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from ui.motion_detection_test_window import MotionDetectionTestWindow
        
        # 创建应用程序实例（如果不存在）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # 测试创建测试窗口（不传递检测工作器）
        test_window = MotionDetectionTestWindow()
        print("  ✅ 运动检测测试窗口创建成功")
        
        # 测试创建带检测工作器的测试窗口（模拟主程序调用）
        test_window_with_worker = MotionDetectionTestWindow(detection_worker=None)
        print("  ✅ 带检测工作器参数的测试窗口创建成功")
        
        # 测试获取当前结果帧方法
        result_frame = test_window.get_current_result_frame()
        print(f"  ✅ 结果帧获取方法正常 (当前结果: {result_frame is not None})")
        
        # 清理
        test_window.close()
        test_window_with_worker.close()
        
        return True
        
    except Exception as e:
        print(f"  ❌ UI组件创建测试失败: {e}")
        return False

def test_opencv_availability():
    """测试OpenCV可用性"""
    print("\n📷 测试OpenCV功能...")
    
    try:
        import cv2
        import numpy as np
        
        # 测试背景减除器创建
        back_sub = cv2.createBackgroundSubtractorKNN(
            history=500,
            dist2Threshold=400.0,
            detectShadows=True
        )
        print("  ✅ KNN背景减除器创建成功")
        
        # 测试基本图像处理
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        fg_mask = back_sub.apply(test_image)
        print("  ✅ 背景减除处理正常")
        
        # 测试高斯模糊
        blurred = cv2.GaussianBlur(fg_mask, (5, 5), 0)
        print("  ✅ 高斯模糊处理正常")
        
        # 测试轮廓检测
        contours, _ = cv2.findContours(blurred, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"  ✅ 轮廓检测正常 (检测到 {len(contours)} 个轮廓)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ OpenCV功能测试失败: {e}")
        return False

def test_integration_readiness():
    """测试集成就绪状态"""
    print("\n🔗 测试集成就绪状态...")
    
    try:
        # 检查必要文件是否存在
        required_files = [
            "ui/main_window.py",
            "ui/motion_detection_test_window.py",
            "utils/config_manager.py",
            "worker/motion_detection_worker.py",
            "config/system_config.json"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            print(f"  ❌ 缺少必要文件: {missing_files}")
            return False
        
        print("  ✅ 所有必要文件都存在")
        
        # 检查菜单集成
        from ui.main_window import MainWindow
        # 这里我们无法直接测试菜单，但可以检查方法是否存在
        if hasattr(MainWindow, '_show_motion_test_window'):
            print("  ✅ 主窗口包含测试界面显示方法")
        else:
            print("  ❌ 主窗口缺少测试界面显示方法")
            return False
            
        if hasattr(MainWindow, '_toggle_detection_result_display'):
            print("  ✅ 主窗口包含显示模式切换方法")
        else:
            print("  ❌ 主窗口缺少显示模式切换方法")
            return False
            
        if hasattr(MainWindow, '_on_test_detection_result'):
            print("  ✅ 主窗口包含检测结果处理方法")
        else:
            print("  ❌ 主窗口缺少检测结果处理方法")
            return False
        
        print("  ✅ 集成功能准备就绪")
        return True
        
    except Exception as e:
        print(f"  ❌ 集成就绪状态测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 运动检测测试界面集成功能测试")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.WARNING)
    
    # 运行所有测试
    tests = [
        ("模块导入测试", test_imports),
        ("配置管理器测试", test_config_manager),
        ("OpenCV功能测试", test_opencv_availability),
        ("UI组件创建测试", test_ui_creation),
        ("集成就绪状态测试", test_integration_readiness)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"  🎉 {test_name}通过")
            else:
                print(f"  ⚠️ {test_name}失败")
        except Exception as e:
            print(f"  💥 {test_name}异常: {e}")
    
    # 输出总结
    print("\n" + "=" * 50)
    print(f"📊 测试结果总结: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！运动检测测试界面已成功集成到主程序。")
        print("\n🚀 使用方法:")
        print("1. 运行主程序: python main.py")
        print("2. 菜单栏 → 设置 → 运动检测测试界面")
        print("3. 菜单栏 → 检测 → 显示运动检测结果")
    else:
        print(f"⚠️ 有 {total - passed} 项测试失败，请检查并修复相关问题。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 