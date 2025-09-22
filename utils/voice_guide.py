#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音指导模块 - 废弃物AI识别指导投放系统
提供文字转语音功能，指导用户投放垃圾
"""

import os
import logging
import threading
from typing import Optional
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
        
        # 初始化
        self._init_tts()
    
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
        
        if async_mode:
            # 异步播放
            threading.Thread(target=self._speak_sync, args=(text,), daemon=True).start()
        else:
            # 同步播放
            self._speak_sync(text)
    
    def _speak_sync(self, text: str):
        """同步播放语音"""
        with self.tts_lock:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.logger.debug(f"播放语音: {text}")
            except Exception as e:
                self.logger.error(f"语音播放失败: {e}")
    
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
        if self.tts_engine:
            try:
                self.tts_engine.stop()
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