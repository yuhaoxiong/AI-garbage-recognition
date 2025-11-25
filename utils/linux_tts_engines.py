#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Linux TTS引擎扩展模块 - 废弃物AI识别指导投放系统
为Linux系统提供高质量的中文语音合成解决方案
"""

import os
import sys
import logging
import subprocess
import threading
import time
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from utils.voice_engine_base import BaseVoiceEngine

# 检查各种TTS引擎的可用性
def check_engine_availability():
    """检查各种TTS引擎的可用性"""
    engines = {}
    
    # 检查Edge-TTS
    try:
        import edge_tts
        engines['edge_tts'] = True
    except ImportError:
        engines['edge_tts'] = False
    
    # 检查Festival
    try:
        subprocess.run(['festival', '--version'], 
                      capture_output=True, check=True, timeout=5)
        engines['festival'] = True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        engines['festival'] = False
    
    # 检查espeak-ng
    try:
        subprocess.run(['espeak-ng', '--version'], 
                      capture_output=True, check=True, timeout=5)
        engines['espeak_ng'] = True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        engines['espeak_ng'] = False
    
    # 检查Ekho
    try:
        subprocess.run(['ekho', '--version'], 
                      capture_output=True, check=True, timeout=5)
        engines['ekho'] = True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        engines['ekho'] = False
    
    # 检查PaddleSpeech
    try:
        import paddlespeech
        engines['paddlespeech'] = True
    except ImportError:
        engines['paddlespeech'] = False
    
    return engines


class EdgeTTSEngine(BaseVoiceEngine):
    """Edge-TTS语音引擎 - 高质量中文语音合成"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.voice_name = "zh-CN-XiaoxiaoNeural"  # 默认中文声音
        self.cache_dir = Path("cache/audio/edge_tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def initialize(self) -> bool:
        """初始化Edge-TTS引擎"""
        try:
            import edge_tts
            
            # 测试基本功能
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Edge-TTS引擎初始化成功")
            return True
            
        except ImportError as e:
            self.logger.error(f"Edge-TTS引擎初始化失败，请安装: pip install edge-tts")
            return False
        except Exception as e:
            self.logger.error(f"Edge-TTS引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            import edge_tts
            import asyncio
            import pygame
            
            # 生成缓存文件名
            cache_key = hashlib.md5(f"{text}_{self.voice_name}".encode()).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}.mp3"
            
            # 如果缓存文件不存在，则生成
            if not cache_file.exists():
                asyncio.run(self._generate_audio_file(text, cache_file))
            
            # 播放音频文件
            if cache_file.exists():
                return self._play_audio_file(cache_file)
            else:
                self.logger.error("无法生成音频文件")
                return False
                
        except Exception as e:
            self.logger.error(f"Edge-TTS语音播放失败: {e}")
            return False
    
    async def _generate_audio_file(self, text: str, output_file: Path):
        """异步生成音频文件"""
        try:
            import edge_tts
            
            # 设置语音参数
            rate = self._convert_rate()
            volume = self._convert_volume()
            
            communicate = edge_tts.Communicate(
                text, 
                self.voice_name,
                rate=rate,
                volume=volume
            )
            
            await communicate.save(str(output_file))
            self.logger.debug(f"Edge-TTS音频文件已生成: {output_file}")
            
        except Exception as e:
            self.logger.error(f"生成Edge-TTS音频文件失败: {e}")
    
    def _play_audio_file(self, audio_file: Path) -> bool:
        """播放音频文件"""
        try:
            import pygame
            # 初始化pygame mixer（仅一次），指定统一参数减少底噪与点击音
            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
                except Exception:
                    pygame.mixer.init()

            # 停止可能残留的播放，避免叠加
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

            # 加载并播放音频，设置音量并加入淡入
            pygame.mixer.music.load(str(audio_file))
            try:
                pygame.mixer.music.set_volume(float(self.config.get('volume', 0.8)))
            except Exception:
                pass
            pygame.mixer.music.play(fade_ms=50)
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"播放音频文件失败: {e}")
            return False
    
    def _convert_rate(self) -> str:
        """转换语速为Edge-TTS格式"""
        rate = self.config.get('speech_rate', 150)
        # Edge-TTS使用百分比格式，如 "+20%" 或 "-20%"
        if rate > 150:
            return f"+{min(100, int((rate - 150) / 150 * 100))}%"
        elif rate < 150:
            return f"-{min(50, int((150 - rate) / 150 * 100))}%"
        else:
            return "+0%"
    
    def _convert_volume(self) -> str:
        """转换音量为Edge-TTS格式"""
        volume = self.config.get('volume', 0.8)
        # Edge-TTS使用百分比格式
        volume_percent = int(volume * 100)
        if volume_percent > 100:
            return "+100%"
        elif volume_percent < 50:
            return f"-{100 - volume_percent}%"
        else:
            return f"+{volume_percent - 100}%"
    
    def stop(self):
        """停止播放"""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            self.logger.error(f"停止Edge-TTS播放失败: {e}")
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用的中文声音"""
        return [
            {'id': 'zh-CN-XiaoxiaoNeural', 'name': '晓晓 (女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunxiNeural', 'name': '云希 (男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-YunyangNeural', 'name': '云扬 (男声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaochenNeural', 'name': '晓辰 (女声)', 'language': 'zh-CN'},
            {'id': 'zh-CN-XiaohanNeural', 'name': '晓涵 (女声)', 'language': 'zh-CN'},
        ]
    
    def set_voice(self, voice_id: str):
        """设置声音"""
        self.voice_name = voice_id
        self.logger.info(f"Edge-TTS声音已设置为: {voice_id}")


class EspeakNGEngine(BaseVoiceEngine):
    """优化的espeak-ng引擎 - 改善中文语音效果"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.process = None
        
    def initialize(self) -> bool:
        """初始化espeak-ng引擎"""
        try:
            # 检查espeak-ng是否可用
            result = subprocess.run(['espeak-ng', '--version'], 
                                  capture_output=True, text=True, check=True)
            
            # 检查中文语音包是否安装
            voices_result = subprocess.run(['espeak-ng', '--voices=zh'], 
                                         capture_output=True, text=True)
            
            if 'zh' not in voices_result.stdout:
                self.logger.warning("espeak-ng中文语音包未安装，语音效果可能较差")
                # 提供安装建议
                self.logger.info("建议安装: sudo apt-get install espeak-ng-data")
            
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Espeak-NG引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Espeak-NG引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            # 优化的espeak-ng命令参数
            cmd = [
                'espeak-ng',
                '-v', 'zh+m3',  # 使用中文男声变体3
                '-s', str(self.config.get('speech_rate', 150)),  # 语速
                '-a', str(int(self.config.get('volume', 0.8) * 200)),  # 音量
                '-p', '50',  # 音调
                '-g', '10',  # 单词间隔
                '--punct=none',  # 不读标点
                text
            ]
            
            # 执行命令
            subprocess.run(cmd, check=True, timeout=30)
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Espeak-NG播放超时")
            return False
        except Exception as e:
            self.logger.error(f"Espeak-NG语音播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=2)
        except Exception as e:
            self.logger.error(f"停止Espeak-NG播放失败: {e}")
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用声音"""
        try:
            result = subprocess.run(['espeak-ng', '--voices=zh'], 
                                  capture_output=True, text=True, check=True)
            
            voices = []
            for line in result.stdout.split('\n')[1:]:  # 跳过标题行
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        voices.append({
                            'id': parts[1],
                            'name': ' '.join(parts[3:]),
                            'language': 'zh'
                        })
            return voices
            
        except Exception as e:
            self.logger.error(f"获取Espeak-NG声音列表失败: {e}")
            return [{'id': 'zh', 'name': '中文', 'language': 'zh'}]


class FestivalEngine(BaseVoiceEngine):
    """Festival语音引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def initialize(self) -> bool:
        """初始化Festival引擎"""
        try:
            # 检查Festival是否可用
            subprocess.run(['festival', '--version'], 
                          capture_output=True, check=True, timeout=5)
            
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Festival引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Festival引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(text)
                temp_file = f.name
            
            try:
                # 使用Festival的文本到语音功能
                cmd = ['festival', '--tts', temp_file]
                subprocess.run(cmd, check=True, timeout=30)
                return True
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Festival语音播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            subprocess.run(['pkill', 'festival'], check=False)
        except Exception as e:
            self.logger.error(f"停止Festival播放失败: {e}")


class EkhoEngine(BaseVoiceEngine):
    """Ekho(余音)语音引擎 - 专为中文设计"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    def initialize(self) -> bool:
        """初始化Ekho引擎"""
        try:
            # 检查Ekho是否可用
            subprocess.run(['ekho', '--version'], 
                          capture_output=True, check=True, timeout=5)
            
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Ekho引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Ekho引擎初始化失败: {e}")
            self.logger.info("可以通过以下方式安装Ekho:")
            self.logger.info("Ubuntu/Debian: sudo apt-get install ekho")
            self.logger.info("或从源码编译: https://github.com/hgneng/ekho")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            cmd = [
                'ekho',
                '-s', str(self.config.get('speech_rate', 150)),  # 语速
                '-p', str(int(self.config.get('volume', 0.8) * 100)),  # 音量
                text
            ]
            
            subprocess.run(cmd, check=True, timeout=30)
            return True
            
        except Exception as e:
            self.logger.error(f"Ekho语音播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            subprocess.run(['pkill', 'ekho'], check=False)
        except Exception as e:
            self.logger.error(f"停止Ekho播放失败: {e}")


class LinuxTTSManager:
    """Linux TTS引擎管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.available_engines = {}
        self.engine_priority = [
            'edge_tts',      # 最高质量
            'ekho',          # 中文专用
            'espeak_ng',     # 优化版espeak
            'festival',      # 备用选择
        ]
        
        self._detect_engines()
    
    def _detect_engines(self):
        """检测可用的TTS引擎"""
        availability = check_engine_availability()
        
        for engine_name in self.engine_priority:
            if availability.get(engine_name, False):
                try:
                    engine = self._create_engine(engine_name)
                    if engine and engine.initialize():
                        self.available_engines[engine_name] = engine
                        self.logger.info(f"Linux TTS引擎已加载: {engine_name}")
                except Exception as e:
                    self.logger.error(f"加载引擎{engine_name}失败: {e}")
        
        if not self.available_engines:
            self.logger.warning("没有可用的Linux TTS引擎")
        else:
            self.logger.info(f"可用的TTS引擎: {list(self.available_engines.keys())}")
    
    def _create_engine(self, engine_name: str) -> Optional[BaseVoiceEngine]:
        """创建TTS引擎实例"""
        engine_classes = {
            'edge_tts': EdgeTTSEngine,
            'espeak_ng': EspeakNGEngine,
            'festival': FestivalEngine,
            'ekho': EkhoEngine,
        }
        
        engine_class = engine_classes.get(engine_name)
        if engine_class:
            return engine_class(self.config)
        return None
    
    def get_best_engine(self) -> Optional[BaseVoiceEngine]:
        """获取最佳可用引擎"""
        for engine_name in self.engine_priority:
            if engine_name in self.available_engines:
                return self.available_engines[engine_name]
        return None
    
    def get_engine(self, engine_name: str) -> Optional[BaseVoiceEngine]:
        """获取指定引擎"""
        return self.available_engines.get(engine_name)
    
    def get_available_engines(self) -> List[str]:
        """获取可用引擎列表"""
        return list(self.available_engines.keys())
    
    def install_recommendations(self) -> Dict[str, str]:
        """获取安装建议"""
        recommendations = {}
        
        availability = check_engine_availability()
        
        if not availability.get('edge_tts', False):
            recommendations['edge_tts'] = "pip install edge-tts"
        
        if not availability.get('espeak_ng', False):
            recommendations['espeak_ng'] = "sudo apt-get install espeak-ng espeak-ng-data"
        
        if not availability.get('festival', False):
            recommendations['festival'] = "sudo apt-get install festival festvox-kallpc16k"
        
        if not availability.get('ekho', False):
            recommendations['ekho'] = "sudo apt-get install ekho 或从源码编译"
        
        return recommendations
