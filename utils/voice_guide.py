#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音指导模块 - 废弃物AI识别指导投放系统
提供文字转语音功能，指导用户投放垃圾
"""

import os
import logging
import threading
import queue
import time
from typing import Optional, Dict, Any
from utils.config_manager import get_config_manager

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("警告: pyttsx3库未安装，语音功能不可用")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("警告: pygame库未安装，音频播放功能受限")


class VoiceGuide:
    """语音指导类"""
    
    def __init__(self):
        """初始化语音指导"""
        self.config_manager = get_config_manager()
        self.logger = logging.getLogger(__name__)
        
        # 语音配置
        try:
            audio_config = self.config_manager.get_audio_config()
            self.enabled = audio_config.enable_voice
            self.language = audio_config.voice_language
            self.volume = audio_config.volume
            self.rate = audio_config.speech_rate
        except Exception as e:
            self.logger.error(f"加载音频配置失败: {e}")
            # 使用默认配置
            self.enabled = True
            self.language = 'zh'
            self.volume = 0.8
            self.rate = 150
        
        # TTS引擎
        self.tts_engine = None
        self.tts_lock = threading.Lock()

        # 语音队列机制
        self.speech_queue = queue.Queue()
        self.speech_worker_running = False
        self.speech_worker_thread = None

        # 初始化
        self._init_tts()
        if self.enabled and TTS_AVAILABLE:
            self._start_speech_worker()
    
    def _init_tts(self):
        """初始化TTS引擎"""
        if not self.enabled or not TTS_AVAILABLE:
            self.logger.info("语音功能已禁用或TTS库不可用")
            return
        
        try:
            self.tts_engine = pyttsx3.init()
            
            # 设置语音属性
            self.tts_engine.setProperty('rate', self.rate)
            self.tts_engine.setProperty('volume', self.volume)
            
            # 设置中文语音（如果可用）
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            self.logger.info("TTS引擎初始化成功")
            
        except Exception as e:
            self.logger.error(f"TTS引擎初始化失败: {e}")
            self.tts_engine = None
    
    def speak(self, text: str, async_mode: bool = True):
        """
        播放语音

        Args:
            text: 要播放的文本
            async_mode: 是否异步播放
        """
        if not self.enabled or not self.tts_engine:
            return

        try:
            # 将语音任务添加到队列
            self.speech_queue.put(text, timeout=1.0)
            self.logger.debug(f"语音任务已加入队列: {text}")
        except queue.Full:
            self.logger.warning("语音队列已满，跳过当前语音")
        except Exception as e:
            self.logger.error(f"添加语音任务失败: {e}")
    
    def _speak_sync(self, text: str):
        """同步播放语音"""
        with self.tts_lock:
            try:
                # 停止之前的语音
                self.tts_engine.stop()

                # 设置新的语音文本
                self.tts_engine.say(text)

                # 使用try-except包装runAndWait以处理事件循环冲突
                try:
                    self.tts_engine.runAndWait()
                except RuntimeError as re:
                    if "run loop already started" in str(re):
                        # 如果事件循环已经启动，使用替代方法
                        self.logger.warning("TTS事件循环冲突，使用替代播放方式")
                        import time
                        time.sleep(len(text) * 0.1)  # 估算播放时间
                    else:
                        raise re

                self.logger.debug(f"播放语音: {text}")
            except Exception as e:
                self.logger.error(f"语音播放失败: {e}")
                # 尝试重新初始化TTS引擎
                self._reinit_tts_engine()

    def _reinit_tts_engine(self):
        """重新初始化TTS引擎"""
        try:
            self.logger.info("尝试重新初始化TTS引擎...")
            if self.tts_engine:
                try:
                    self.tts_engine.stop()
                except:
                    pass

            # 重新初始化
            self._init_tts()
            self.logger.info("TTS引擎重新初始化成功")
        except Exception as e:
            self.logger.error(f"TTS引擎重新初始化失败: {e}")
            self.tts_engine = None

    def _start_speech_worker(self):
        """启动语音工作器线程"""
        if self.speech_worker_running:
            return

        self.speech_worker_running = True
        self.speech_worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_worker_thread.start()
        self.logger.info("语音工作器线程已启动")

    def _speech_worker(self):
        """语音工作器线程主循环"""
        while self.speech_worker_running:
            try:
                # 从队列获取语音任务
                text = self.speech_queue.get(timeout=1.0)

                if text and self.tts_engine:
                    self._speak_sync_safe(text)

                # 标记任务完成
                self.speech_queue.task_done()

            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                self.logger.error(f"语音工作器处理失败: {e}")
                time.sleep(0.1)

    def _speak_sync_safe(self, text: str):
        """安全的同步语音播放"""
        try:
            with self.tts_lock:
                # 停止之前的语音
                try:
                    self.tts_engine.stop()
                except:
                    pass

                # 设置新的语音文本
                self.tts_engine.say(text)

                # 安全的播放方式
                try:
                    self.tts_engine.runAndWait()
                except RuntimeError as re:
                    if "run loop already started" in str(re):
                        # 事件循环冲突，使用估算时间等待
                        self.logger.debug("TTS事件循环冲突，使用估算等待时间")
                        estimated_time = len(text) * 0.08  # 估算播放时间
                        time.sleep(max(1.0, estimated_time))
                    else:
                        raise re

                self.logger.debug(f"安全播放语音完成: {text}")

        except Exception as e:
            self.logger.error(f"安全语音播放失败: {e}")
            # 尝试重新初始化
            if "run loop already started" not in str(e):
                self._reinit_tts_engine()
    
    def speak_guidance(self, waste_category: str, guidance_text: str = None):
        """
        播放垃圾投放指导语音
        
        Args:
            waste_category: 垃圾分类
            guidance_text: 自定义指导文本
        """
        if guidance_text:
            text = guidance_text
        else:
            # 从配置获取指导文本
            category_info = self.config_manager.get_waste_category_info(waste_category)
            if category_info:
                text = category_info.get('guidance', f'请将{waste_category}投放到对应垃圾桶')
            else:
                text = f'检测到{waste_category}，请咨询工作人员投放方式'
        
        # 添加前缀提示
        full_text = f"检测到{waste_category}。{text}"
        
        self.speak(full_text)
    
    def speak_welcome(self):
        """播放欢迎语音"""
        welcome_text = "欢迎使用智能垃圾分类指导系统，请将废弃物放在摄像头前进行识别"
        self.speak(welcome_text)
    
    def speak_error(self, error_message: str = None):
        """播放错误提示语音"""
        if error_message:
            text = f"系统错误：{error_message}"
        else:
            text = "系统出现错误，请联系工作人员"
        
        self.speak(text)
    
    def speak_no_detection(self):
        """播放未检测到物品的语音"""
        text = "未检测到可识别的废弃物，请重新放置或咨询工作人员"
        self.speak(text)
    
    def speak_multiple_items(self, count: int):
        """播放检测到多个物品的语音"""
        text = f"检测到{count}个废弃物，请分别按照指导投放"
        self.speak(text)
    
    def set_volume(self, volume: float):
        """
        设置音量
        
        Args:
            volume: 音量 (0.0-1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        if self.tts_engine:
            self.tts_engine.setProperty('volume', self.volume)
        
        # 更新配置
        self.config_manager.update_config('system', 'audio.volume', self.volume)
    
    def set_rate(self, rate: int):
        """
        设置语速
        
        Args:
            rate: 语速 (50-300)
        """
        self.rate = max(50, min(300, rate))
        if self.tts_engine:
            self.tts_engine.setProperty('rate', self.rate)
        
        # 更新配置
        self.config_manager.update_config('system', 'audio.speech_rate', self.rate)
    
    def enable_voice(self, enabled: bool):
        """
        启用/禁用语音功能
        
        Args:
            enabled: 是否启用
        """
        self.enabled = enabled
        
        # 更新配置
        self.config_manager.update_config('system', 'audio.enable_voice', self.enabled)
        
        if enabled and not self.tts_engine:
            self._init_tts()
    
    def stop_all_speech(self):
        """停止所有语音播放"""
        try:
            # 停止语音工作器
            self.speech_worker_running = False

            # 清空队列
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except queue.Empty:
                    break

            # 停止TTS引擎
            if self.tts_engine:
                self.tts_engine.stop()

            # 等待工作器线程结束
            if self.speech_worker_thread and self.speech_worker_thread.is_alive():
                self.speech_worker_thread.join(timeout=2.0)

            self.logger.info("所有语音播放已停止")

        except Exception as e:
            self.logger.error(f"停止语音播放失败: {e}")


class AudioPlayer:
    """音频播放器（用于播放提示音等）"""
    
    def __init__(self):
        """初始化音频播放器"""
        self.logger = logging.getLogger(__name__)
        self.pygame_initialized = False
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.pygame_initialized = True
                self.logger.info("pygame音频播放器初始化成功")
            except Exception as e:
                self.logger.error(f"pygame初始化失败: {e}")
    
    def play_notification_sound(self):
        """播放通知提示音"""
        if not self.pygame_initialized:
            return
        
        try:
            # 这里可以播放自定义的提示音文件
            # sound = pygame.mixer.Sound("sounds/notification.wav")
            # sound.play()
            pass
        except Exception as e:
            self.logger.error(f"播放提示音失败: {e}")
    
    def play_success_sound(self):
        """播放成功提示音"""
        if not self.pygame_initialized:
            return
        
        try:
            # sound = pygame.mixer.Sound("sounds/success.wav")
            # sound.play()
            pass
        except Exception as e:
            self.logger.error(f"播放成功音失败: {e}")
    
    def play_error_sound(self):
        """播放错误提示音"""
        if not self.pygame_initialized:
            return
        
        try:
            # sound = pygame.mixer.Sound("sounds/error.wav")
            # sound.play()
            pass
        except Exception as e:
            self.logger.error(f"播放错误音失败: {e}")


# 全局实例
_voice_guide = None
_audio_player = None

def get_voice_guide() -> VoiceGuide:
    """获取全局语音指导实例"""
    global _voice_guide
    if _voice_guide is None:
        _voice_guide = VoiceGuide()
    return _voice_guide

def get_audio_player() -> AudioPlayer:
    """获取全局音频播放器实例"""
    global _audio_player
    if _audio_player is None:
        _audio_player = AudioPlayer()
    return _audio_player 