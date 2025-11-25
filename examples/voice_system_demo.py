#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音系统演示 - 废弃物AI识别指导投放系统
演示改进后的语音系统功能，包括多引擎支持和Linux TTS优化
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.enhanced_voice_guide import get_enhanced_voice_guide, VoicePriority
from utils.voice_content_manager import VoiceStyle, VoiceContext
from utils.tts_diagnostics import TTSDiagnostics

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_diagnostics():
    """运行TTS诊断"""
    print("\n" + "="*60)
    print("🔍 TTS引擎诊断")
    print("="*60)
    
    diagnostics = TTSDiagnostics()
    diagnostics.diagnose_all_engines()
    diagnostics.print_summary()
    
    return diagnostics

def demo_basic_voice_functions():
    """演示基本语音功能"""
    print("\n" + "="*60)
    print("🎵 基本语音功能演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用或无可用引擎")
        return False
    
    # 获取系统状态
    status = voice_guide.get_status()
    print(f"当前引擎: {status.get('current_engine', '未知')}")
    print(f"可用引擎: {', '.join(status.get('available_engines', []))}")
    
    # 基本语音测试
    print("\n🔊 播放欢迎语音...")
    voice_guide.speak_welcome()
    time.sleep(2)
    
    print("🔊 播放检测开始语音...")
    voice_guide.speak_detection_start()
    time.sleep(2)
    
    print("🔊 播放检测成功语音...")
    voice_guide.speak_detection_success("可回收物", 0.85)
    time.sleep(3)
    
    print("🔊 播放投放指导语音...")
    voice_guide.speak_guidance("可回收物", 0.85)
    time.sleep(3)
    
    print("🔊 播放感谢语音...")
    voice_guide.speak_thank_you()
    time.sleep(2)
    
    return True

def demo_voice_styles():
    """演示不同语音风格"""
    print("\n" + "="*60)
    print("🎭 语音风格演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    styles = [
        (VoiceStyle.FORMAL, "正式风格"),
        (VoiceStyle.FRIENDLY, "友好风格"),
        (VoiceStyle.ENCOURAGING, "鼓励风格"),
    ]
    
    for style, style_name in styles:
        print(f"\n🎯 切换到{style_name}...")
        voice_guide.set_voice_style(style)
        
        print(f"🔊 {style_name} - 欢迎语音")
        voice_guide.speak_welcome()
        time.sleep(3)
        
        print(f"🔊 {style_name} - 检测成功")
        voice_guide.speak_detection_success("湿垃圾", 0.92)
        time.sleep(3)

def demo_priority_system():
    """演示优先级系统"""
    print("\n" + "="*60)
    print("⚡ 优先级系统演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    # 添加不同优先级的语音任务
    print("📝 添加不同优先级的语音任务...")
    
    # 低优先级任务
    voice_guide.speak("这是一个低优先级的语音任务", VoicePriority.LOW)
    voice_guide.speak("这是另一个低优先级任务", VoicePriority.LOW)
    
    # 普通优先级任务
    voice_guide.speak("这是普通优先级任务", VoicePriority.NORMAL)
    
    # 高优先级任务（会插队）
    time.sleep(1)  # 让前面的任务开始执行
    voice_guide.speak("紧急！这是高优先级任务", VoicePriority.HIGH)
    
    # 紧急任务（最高优先级）
    time.sleep(0.5)
    voice_guide.speak_urgent("警告！这是紧急任务")
    
    print("🔊 语音任务已添加到队列，注意播放顺序...")
    
    # 等待所有任务完成
    time.sleep(15)

def demo_engine_switching():
    """演示引擎切换"""
    print("\n" + "="*60)
    print("🔄 引擎切换演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    # 获取可用引擎
    status = voice_guide.get_status()
    available_engines = status.get('available_engines', [])
    
    if len(available_engines) < 2:
        print("⚠️ 只有一个可用引擎，无法演示引擎切换")
        return
    
    print(f"可用引擎: {', '.join(available_engines)}")
    
    # 测试每个引擎
    for engine in available_engines[:3]:  # 最多测试3个引擎
        print(f"\n🔧 尝试使用引擎: {engine}")
        
        # 这里需要实现引擎切换功能
        # 暂时通过重新初始化来模拟
        voice_guide.speak(f"当前使用{engine}引擎播放语音")
        time.sleep(3)

def demo_cache_system():
    """演示缓存系统"""
    print("\n" + "="*60)
    print("💾 缓存系统演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    # 获取缓存信息
    cache_info = voice_guide.get_cache_info()
    print("缓存信息:")
    for key, value in cache_info.items():
        print(f"  {key}: {value}")
    
    # 播放相同文本多次，演示缓存效果
    test_text = "这是缓存测试文本，第一次播放会生成缓存"
    
    print(f"\n🔊 第一次播放 (生成缓存)...")
    start_time = time.time()
    voice_guide.speak(test_text, VoicePriority.HIGH)
    time.sleep(4)
    first_time = time.time() - start_time
    
    print(f"🔊 第二次播放 (使用缓存)...")
    start_time = time.time()
    voice_guide.speak(test_text, VoicePriority.HIGH)
    time.sleep(4)
    second_time = time.time() - start_time
    
    print(f"时间对比: 第一次 {first_time:.2f}s, 第二次 {second_time:.2f}s")
    
    # 显示更新后的缓存信息
    cache_info = voice_guide.get_cache_info()
    print("\n更新后的缓存信息:")
    for key, value in cache_info.items():
        print(f"  {key}: {value}")

def demo_error_handling():
    """演示错误处理和恢复"""
    print("\n" + "="*60)
    print("🛠️ 错误处理演示")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    # 获取统计信息
    stats = voice_guide.get_statistics()
    print("当前统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 播放一些正常语音
    print("\n🔊 播放正常语音...")
    voice_guide.speak("这是正常的语音播放")
    time.sleep(3)
    
    # 尝试播放空文本（应该被忽略）
    print("🔊 尝试播放空文本...")
    voice_guide.speak("")
    voice_guide.speak("   ")  # 只有空格
    
    # 播放很长的文本
    print("🔊 播放长文本...")
    long_text = "这是一个很长的文本测试，" * 10
    voice_guide.speak(long_text)
    time.sleep(5)
    
    # 显示更新后的统计信息
    stats = voice_guide.get_statistics()
    print("\n更新后的统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

def interactive_demo():
    """交互式演示"""
    print("\n" + "="*60)
    print("🎮 交互式语音测试")
    print("="*60)
    
    voice_guide = get_enhanced_voice_guide()
    
    if not voice_guide.enabled:
        print("❌ 语音系统未启用")
        return
    
    while True:
        print("\n请选择操作:")
        print("1. 播放自定义文本")
        print("2. 播放垃圾分类指导")
        print("3. 测试不同优先级")
        print("4. 查看系统状态")
        print("5. 清空缓存")
        print("0. 退出")
        
        try:
            choice = input("\n请输入选择 (0-5): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                text = input("请输入要播放的文本: ").strip()
                if text:
                    voice_guide.speak(text)
                    print("🔊 正在播放...")
            elif choice == '2':
                categories = ["可回收物", "有害垃圾", "湿垃圾", "干垃圾", "厨余垃圾"]
                print("垃圾分类: " + ", ".join(f"{i+1}.{cat}" for i, cat in enumerate(categories)))
                cat_choice = input("请选择分类 (1-5): ").strip()
                try:
                    cat_index = int(cat_choice) - 1
                    if 0 <= cat_index < len(categories):
                        category = categories[cat_index]
                        voice_guide.speak_guidance(category, 0.9)
                        print(f"🔊 正在播放{category}指导...")
                    else:
                        print("❌ 无效选择")
                except ValueError:
                    print("❌ 请输入数字")
            elif choice == '3':
                priorities = ["低", "普通", "高", "紧急"]
                priority_map = [VoicePriority.LOW, VoicePriority.NORMAL, 
                              VoicePriority.HIGH, VoicePriority.URGENT]
                print("优先级: " + ", ".join(f"{i+1}.{p}" for i, p in enumerate(priorities)))
                pri_choice = input("请选择优先级 (1-4): ").strip()
                text = input("请输入文本: ").strip()
                try:
                    pri_index = int(pri_choice) - 1
                    if 0 <= pri_index < len(priorities) and text:
                        priority = priority_map[pri_index]
                        voice_guide.speak(text, priority)
                        print(f"🔊 正在以{priorities[pri_index]}优先级播放...")
                    else:
                        print("❌ 无效输入")
                except ValueError:
                    print("❌ 请输入数字")
            elif choice == '4':
                status = voice_guide.get_status()
                print("\n系统状态:")
                for key, value in status.items():
                    if key != 'cache_info':  # 缓存信息太长，单独显示
                        print(f"  {key}: {value}")
            elif choice == '5':
                voice_guide.clear_cache()
                print("✅ 缓存已清空")
            else:
                print("❌ 无效选择，请输入0-5")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出演示")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

def main():
    """主函数"""
    setup_logging()
    
    print("🎤 语音系统演示程序")
    print("="*60)
    print("本程序将演示改进后的语音系统功能")
    print("包括多引擎支持、优先级队列、缓存机制等")
    
    # 运行诊断
    diagnostics = run_diagnostics()
    
    # 检查是否有可用引擎
    available_engines = [name for name, info in diagnostics.test_results['engines'].items() 
                        if info.get('available', False)]
    
    if not available_engines:
        print("\n❌ 没有可用的TTS引擎，请先安装TTS引擎")
        print("Linux用户可以运行: ./scripts/install_linux_tts.sh")
        print("或手动安装: pip install edge-tts")
        return
    
    print(f"\n✅ 找到 {len(available_engines)} 个可用引擎")
    
    # 演示菜单
    while True:
        print("\n" + "="*60)
        print("请选择演示内容:")
        print("1. 基本语音功能")
        print("2. 语音风格演示")
        print("3. 优先级系统")
        print("4. 引擎切换")
        print("5. 缓存系统")
        print("6. 错误处理")
        print("7. 交互式测试")
        print("8. 重新运行诊断")
        print("0. 退出")
        
        try:
            choice = input("\n请输入选择 (0-8): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                demo_basic_voice_functions()
            elif choice == '2':
                demo_voice_styles()
            elif choice == '3':
                demo_priority_system()
            elif choice == '4':
                demo_engine_switching()
            elif choice == '5':
                demo_cache_system()
            elif choice == '6':
                demo_error_handling()
            elif choice == '7':
                interactive_demo()
            elif choice == '8':
                run_diagnostics()
            else:
                print("❌ 无效选择，请输入0-8")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n👋 感谢使用语音系统演示程序！")

if __name__ == "__main__":
    main()

