#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS诊断工具 - 废弃物AI识别指导投放系统
提供语音引擎诊断、配置和性能测试功能
"""

import os
import sys
import logging
import time
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json

class TTSDiagnostics:
    """TTS诊断工具类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system_info = self._get_system_info()
        self.test_results = {}
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version(),
            'distribution': self._get_linux_distribution() if platform.system() == 'Linux' else None
        }
    
    def _get_linux_distribution(self) -> Optional[str]:
        """获取Linux发行版信息"""
        try:
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=')[1].strip().strip('"')
        except:
            pass
        return None
    
    def diagnose_all_engines(self) -> Dict[str, Any]:
        """诊断所有TTS引擎"""
        self.logger.info("开始TTS引擎全面诊断...")
        
        results = {
            'system_info': self.system_info,
            'engines': {},
            'recommendations': [],
            'timestamp': time.time()
        }
        
        # 测试各种引擎
        engines_to_test = [
            ('pyttsx3', self._test_pyttsx3),
            ('pygame', self._test_pygame),
            ('edge_tts', self._test_edge_tts),
            ('espeak', self._test_espeak),
            ('espeak_ng', self._test_espeak_ng),
            ('festival', self._test_festival),
            ('ekho', self._test_ekho),
        ]
        
        if sys.platform == 'win32':
            engines_to_test.append(('sapi', self._test_sapi))
        
        for engine_name, test_func in engines_to_test:
            self.logger.info(f"测试引擎: {engine_name}")
            try:
                engine_result = test_func()
                results['engines'][engine_name] = engine_result
                self.logger.info(f"{engine_name}: {'可用' if engine_result['available'] else '不可用'}")
            except Exception as e:
                self.logger.error(f"测试{engine_name}时出错: {e}")
                results['engines'][engine_name] = {
                    'available': False,
                    'error': str(e),
                    'quality_score': 0
                }
        
        # 生成建议
        results['recommendations'] = self._generate_recommendations(results['engines'])
        
        self.test_results = results
        return results
    
    def _test_pyttsx3(self) -> Dict[str, Any]:
        """测试pyttsx3引擎"""
        result = {
            'available': False,
            'voices': [],
            'chinese_support': False,
            'quality_score': 0,
            'performance': {},
            'issues': []
        }
        
        try:
            import pyttsx3
            
            engine = pyttsx3.init()
            result['available'] = True
            
            # 获取声音列表
            voices = engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_info = {
                        'id': voice.id,
                        'name': voice.name,
                        'languages': getattr(voice, 'languages', [])
                    }
                    result['voices'].append(voice_info)
                    
                    # 检查中文支持
                    if any('zh' in str(lang).lower() or 'chinese' in voice.name.lower() 
                           for lang in getattr(voice, 'languages', [])):
                        result['chinese_support'] = True
            
            # 性能测试
            test_text = "测试文本"
            start_time = time.time()
            engine.say(test_text)
            try:
                engine.runAndWait()
                result['performance']['synthesis_time'] = time.time() - start_time
            except RuntimeError as e:
                if "run loop already started" in str(e):
                    result['issues'].append("事件循环冲突")
                    result['performance']['synthesis_time'] = 1.0  # 估算
                else:
                    raise
            
            # 质量评分
            base_score = 60
            if result['chinese_support']:
                base_score += 20
            if len(result['voices']) > 1:
                base_score += 10
            if not result['issues']:
                base_score += 10
            
            result['quality_score'] = min(100, base_score)
            
        except ImportError:
            result['error'] = "pyttsx3未安装"
        except Exception as e:
            result['error'] = str(e)
            result['issues'].append(f"初始化失败: {e}")
        
        return result
    
    def _test_pygame(self) -> Dict[str, Any]:
        """测试pygame音频播放"""
        result = {
            'available': False,
            'audio_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        try:
            import pygame
            pygame.mixer.init()
            result['available'] = True
            result['audio_support'] = True
            result['quality_score'] = 80  # pygame主要用于音频播放
            
        except ImportError:
            result['error'] = "pygame未安装"
        except Exception as e:
            result['error'] = str(e)
            result['issues'].append(f"音频初始化失败: {e}")
        
        return result
    
    def _test_edge_tts(self) -> Dict[str, Any]:
        """测试Edge-TTS引擎"""
        result = {
            'available': False,
            'voices': [],
            'chinese_support': False,
            'quality_score': 0,
            'performance': {},
            'network_required': True,
            'issues': []
        }
        
        try:
            import edge_tts
            import asyncio
            
            result['available'] = True
            result['chinese_support'] = True
            
            # 获取中文声音列表
            chinese_voices = [
                {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓 (女声)', 'language': 'zh-CN'},
                {'id': 'zh-CN-YunxiNeural', 'name': '云希 (男声)', 'language': 'zh-CN'},
                {'id': 'zh-CN-YunyangNeural', 'name': '云扬 (男声)', 'language': 'zh-CN'},
            ]
            result['voices'] = chinese_voices
            
            # 性能测试（简单测试，不实际生成音频）
            result['performance']['estimated_quality'] = 'high'
            
            # 质量评分 - Edge-TTS是最高质量的
            result['quality_score'] = 95
            
            # 检查网络连接
            try:
                import urllib.request
                urllib.request.urlopen('https://speech.platform.bing.com', timeout=5)
            except:
                result['issues'].append("网络连接问题，可能影响使用")
                result['quality_score'] -= 10
            
        except ImportError:
            result['error'] = "edge-tts未安装"
        except Exception as e:
            result['error'] = str(e)
            result['issues'].append(f"初始化失败: {e}")
        
        return result
    
    def _test_espeak(self) -> Dict[str, Any]:
        """测试espeak引擎"""
        result = {
            'available': False,
            'chinese_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        try:
            # 检查espeak命令是否可用
            proc = subprocess.run(['espeak', '--version'], 
                                capture_output=True, text=True, timeout=5)
            result['available'] = True
            
            # 检查中文支持
            voices_proc = subprocess.run(['espeak', '--voices=zh'], 
                                       capture_output=True, text=True, timeout=5)
            if 'zh' in voices_proc.stdout:
                result['chinese_support'] = True
                result['quality_score'] = 40  # espeak中文质量较低
            else:
                result['quality_score'] = 30
                result['issues'].append("中文语音包未安装")
            
        except FileNotFoundError:
            result['error'] = "espeak未安装"
        except subprocess.TimeoutExpired:
            result['error'] = "espeak响应超时"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _test_espeak_ng(self) -> Dict[str, Any]:
        """测试espeak-ng引擎"""
        result = {
            'available': False,
            'chinese_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        try:
            # 检查espeak-ng命令是否可用
            proc = subprocess.run(['espeak-ng', '--version'], 
                                capture_output=True, text=True, timeout=5)
            result['available'] = True
            
            # 检查中文支持
            voices_proc = subprocess.run(['espeak-ng', '--voices=zh'], 
                                       capture_output=True, text=True, timeout=5)
            if 'zh' in voices_proc.stdout:
                result['chinese_support'] = True
                result['quality_score'] = 55  # espeak-ng比espeak稍好
            else:
                result['quality_score'] = 45
                result['issues'].append("中文语音包未安装")
            
        except FileNotFoundError:
            result['error'] = "espeak-ng未安装"
        except subprocess.TimeoutExpired:
            result['error'] = "espeak-ng响应超时"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _test_festival(self) -> Dict[str, Any]:
        """测试Festival引擎"""
        result = {
            'available': False,
            'chinese_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        try:
            # 检查Festival命令是否可用
            proc = subprocess.run(['festival', '--version'], 
                                capture_output=True, text=True, timeout=5)
            result['available'] = True
            result['quality_score'] = 50  # Festival主要支持英文
            result['issues'].append("主要支持英文，中文支持有限")
            
        except FileNotFoundError:
            result['error'] = "Festival未安装"
        except subprocess.TimeoutExpired:
            result['error'] = "Festival响应超时"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _test_ekho(self) -> Dict[str, Any]:
        """测试Ekho引擎"""
        result = {
            'available': False,
            'chinese_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        try:
            # 检查Ekho命令是否可用
            proc = subprocess.run(['ekho', '--version'], 
                                capture_output=True, text=True, timeout=5)
            result['available'] = True
            result['chinese_support'] = True
            result['quality_score'] = 75  # Ekho专为中文设计
            
        except FileNotFoundError:
            result['error'] = "Ekho未安装"
        except subprocess.TimeoutExpired:
            result['error'] = "Ekho响应超时"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _test_sapi(self) -> Dict[str, Any]:
        """测试Windows SAPI引擎"""
        result = {
            'available': False,
            'voices': [],
            'chinese_support': False,
            'quality_score': 0,
            'issues': []
        }
        
        if sys.platform != 'win32':
            result['error'] = "SAPI仅在Windows上可用"
            return result
        
        try:
            import win32com.client
            
            sapi = win32com.client.Dispatch("SAPI.SpVoice")
            result['available'] = True
            
            # 获取声音列表
            voices = sapi.GetVoices()
            for i in range(voices.Count):
                voice = voices.Item(i)
                voice_info = {
                    'id': voice.Id,
                    'name': voice.GetDescription()
                }
                result['voices'].append(voice_info)
                
                # 检查中文支持
                if 'chinese' in voice.GetDescription().lower() or 'zh' in voice.Id.lower():
                    result['chinese_support'] = True
            
            # 质量评分
            base_score = 70
            if result['chinese_support']:
                base_score += 15
            if len(result['voices']) > 2:
                base_score += 10
            
            result['quality_score'] = min(100, base_score)
            
        except ImportError:
            result['error'] = "pywin32未安装"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _generate_recommendations(self, engines: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 统计可用引擎
        available_engines = [name for name, info in engines.items() 
                           if info.get('available', False)]
        
        if not available_engines:
            recommendations.append("⚠️ 没有可用的TTS引擎，请安装至少一个TTS引擎")
            
        # 根据平台给出建议
        if sys.platform.startswith('linux'):
            # Linux建议
            if 'edge_tts' not in available_engines:
                recommendations.append("🔧 建议安装Edge-TTS获得最高质量中文语音: pip install edge-tts")
            
            if 'ekho' not in available_engines:
                recommendations.append("🔧 建议安装Ekho获得更好的中文支持: sudo apt-get install ekho")
            
            if 'espeak_ng' not in available_engines:
                recommendations.append("🔧 建议安装espeak-ng替代espeak: sudo apt-get install espeak-ng")
                
            # 检查espeak中文支持
            if 'espeak' in available_engines:
                espeak_info = engines['espeak']
                if not espeak_info.get('chinese_support', False):
                    recommendations.append("🔧 安装espeak中文语音包: sudo apt-get install espeak-data")
                    
        elif sys.platform == 'win32':
            # Windows建议
            if 'sapi' not in available_engines:
                recommendations.append("🔧 建议安装pywin32以使用Windows SAPI: pip install pywin32")
            
            if 'edge_tts' not in available_engines:
                recommendations.append("🔧 建议安装Edge-TTS获得最高质量语音: pip install edge-tts")
        
        # 通用建议
        if 'pygame' not in available_engines:
            recommendations.append("🔧 建议安装pygame支持音频播放: pip install pygame")
        
        # 质量建议
        high_quality_engines = [name for name, info in engines.items() 
                              if info.get('available', False) and info.get('quality_score', 0) >= 70]
        
        if not high_quality_engines:
            recommendations.append("💡 当前没有高质量TTS引擎，建议安装Edge-TTS或Ekho")
        
        # 中文支持建议
        chinese_engines = [name for name, info in engines.items() 
                          if info.get('available', False) and info.get('chinese_support', False)]
        
        if not chinese_engines:
            recommendations.append("⚠️ 当前没有支持中文的TTS引擎，中文语音效果可能较差")
        
        return recommendations
    
    def save_report(self, filepath: Optional[str] = None) -> str:
        """保存诊断报告"""
        if not self.test_results:
            self.diagnose_all_engines()
        
        if filepath is None:
            filepath = f"tts_diagnosis_report_{int(time.time())}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"诊断报告已保存到: {filepath}")
        return filepath
    
    def print_summary(self):
        """打印诊断摘要"""
        if not self.test_results:
            self.diagnose_all_engines()
        
        print("\n" + "="*60)
        print("TTS引擎诊断报告")
        print("="*60)
        
        # 系统信息
        print(f"\n系统信息:")
        print(f"  平台: {self.system_info['platform']} {self.system_info['architecture']}")
        print(f"  Python: {self.system_info['python_version']}")
        if self.system_info.get('distribution'):
            print(f"  发行版: {self.system_info['distribution']}")
        
        # 引擎状态
        print(f"\n引擎状态:")
        for name, info in self.test_results['engines'].items():
            status = "✓ 可用" if info.get('available') else "✗ 不可用"
            quality = info.get('quality_score', 0)
            chinese = "🇨🇳" if info.get('chinese_support') else ""
            
            print(f"  {name:12} {status:8} 质量:{quality:3d}/100 {chinese}")
            
            if info.get('issues'):
                for issue in info['issues']:
                    print(f"    ⚠️  {issue}")
        
        # 建议
        if self.test_results['recommendations']:
            print(f"\n改进建议:")
            for rec in self.test_results['recommendations']:
                print(f"  {rec}")
        
        # 推荐引擎
        available_engines = [(name, info) for name, info in self.test_results['engines'].items() 
                           if info.get('available', False)]
        
        if available_engines:
            # 按质量排序
            available_engines.sort(key=lambda x: x[1].get('quality_score', 0), reverse=True)
            
            print(f"\n推荐使用顺序 (按质量排序):")
            for i, (name, info) in enumerate(available_engines, 1):
                quality = info.get('quality_score', 0)
                chinese = "支持中文" if info.get('chinese_support') else "不支持中文"
                print(f"  {i}. {name} (质量:{quality}/100, {chinese})")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TTS引擎诊断工具')
    parser.add_argument('--save', '-s', help='保存报告到文件')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # 运行诊断
    diagnostics = TTSDiagnostics()
    diagnostics.diagnose_all_engines()
    
    # 打印摘要
    if not args.quiet:
        diagnostics.print_summary()
    
    # 保存报告
    if args.save:
        diagnostics.save_report(args.save)
        print(f"\n报告已保存到: {args.save}")


if __name__ == "__main__":
    main()

