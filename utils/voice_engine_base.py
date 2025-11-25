#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音引擎基类模块 - 废弃物AI识别指导投放系统
提供所有语音引擎的基础接口，避免循环导入
"""

import logging
import threading
from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseVoiceEngine(ABC):
    """语音引擎基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.is_available = False
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化引擎"""
        pass
    
    @abstractmethod
    def speak(self, text: str) -> bool:
        """播放语音"""
        pass
    
    def stop(self):
        """停止播放"""
        raise NotImplementedError
    
    def set_property(self, name: str, value: Any):
        """设置属性"""
        raise NotImplementedError
    
    def get_voices(self) -> list:
        """获取可用声音"""
        return []
    
    def cleanup(self):
        """清理资源"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'initialized': self.is_initialized,
            'available': self.is_available,
            'name': self.__class__.__name__
        }
