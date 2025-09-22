#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运动检测功能检查脚本 - 废弃物AI识别指导投放系统
检查运动检测相关的配置和功能状态
"""

import os
import json
import sys
import logging
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_config_file():
    """检查配置文件"""
    print("🔧 检查配置文件...")
    
    config_file = "config/system_config.json"
    if not os.path.exists(config_file):
        print("  ❌ 配置文件不存在：config/system_config.json")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查运动检测配置
        motion_config = config.get('motion_detection', {})
        enable_motion = motion_config.get('enable_motion_detection', False)
        
        print(f"  ✅ 配置文件存在")
        print(f"  📊 运动检测启用状态: {'✅ 启用' if enable_motion else '❌ 禁用'}")
        
        if enable_motion:
            print(f"    - 运动阈值: {motion_config.get('motion_threshold', 'N/A')}")
            print(f"    - 最小轮廓面积: {motion_config.get('min_contour_area', 'N/A')}")
            print(f"    - 冷却时间: {motion_config.get('detection_cooldown', 'N/A')}秒")
        
        # 检查API配置
        api_config = config.get('api', {})
        api_url = api_config.get('api_url', '')
        api_key = api_config.get('api_key', '')
        
        print(f"  🌐 API配置:")
        print(f"    - API URL: {api_url if api_url else '❌ 未配置'}")
        print(f"    - API密钥: {'✅ 已配置' if api_key and len(api_key) > 10 else '❌ 未配置或无效'}")
        print(f"    - 模型名称: {api_config.get('model_name', 'N/A')}")
        
        return enable_motion and api_url and api_key
        
    except Exception as e:
        print(f"  ❌ 读取配置文件失败: {e}")
        return False

def main():
    """主函数"""
    print("🔍 运动检测功能检查工具")
    print("=" * 50)
    
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    
    # 检查配置文件
    config_ok = check_config_file()
    
    print("\n💡 使用说明:")
    print("1. 启动主程序: python main.py")
    print("2. 菜单栏 → 检测 → 运动检测模式")
    print("3. 点击'开始检测'按钮")
    print("4. 在摄像头前挥手触发检测")
    
    if config_ok:
        print("\n🎉 配置检查通过！可以尝试启用运动检测功能。")
    else:
        print("\n⚠️ 配置有问题，请检查配置文件。")
    
    return config_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 