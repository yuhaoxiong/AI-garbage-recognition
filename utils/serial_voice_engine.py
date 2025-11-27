#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口语音引擎模块 - 废弃物AI识别指导投放系统
适配 ETV001-485 语音模块 (科星私有协议)
"""

import time
import logging
import threading
from typing import Dict, Any, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from utils.voice_engine_base import BaseVoiceEngine

class SerialVoiceEngine(BaseVoiceEngine):
    """
    基于串口的语音引擎 (ETV001-485)
    协议: 科星私有协议 (# + 内容)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.serial_port: Optional[serial.Serial] = None
        self.lock = threading.Lock()
        
        # 配置参数
        self.port = config.get('port', '/dev/ttyS3')
        self.baudrate = config.get('baudrate', 9600)
        self.encoding = config.get('encoding', 'gb2312')
        self.timeout = config.get('timeout', 1.0)
        
    def initialize(self) -> bool:
        """初始化串口连接"""
        if not SERIAL_AVAILABLE:
            self.logger.error("未安装 pyserial 库，无法使用串口语音引擎")
            return False
            
        try:
            with self.lock:
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()
                
                self.serial_port = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=self.timeout
                )
                
                if not self.serial_port.is_open:
                    self.serial_port.open()
                
                self.is_initialized = True
                self.is_available = True
                self.logger.info(f"串口语音引擎初始化成功: {self.port} @ {self.baudrate}")
                return True
                
        except Exception as e:
            self.logger.error(f"串口语音引擎初始化失败: {e}")
            self.is_initialized = False
            self.is_available = False
            return False
            
    def speak(self, text: str) -> bool:
        """
        播放语音
        Args:
            text: 要播放的文本
        Returns:
            bool: 发送是否成功
        """
        if not self.is_initialized or not self.serial_port:
            if not self.initialize():
                return False
        
        try:
            with self.lock:
                # 协议格式: # + 内容
                content = f"#{text}"
                
                # 编码
                try:
                    data = content.encode(self.encoding)
                except UnicodeEncodeError:
                    self.logger.warning(f"字符编码失败 ({self.encoding})，尝试使用 gb18030")
                    data = content.encode('gb18030')
                
                # 发送
                self.serial_port.write(data)
                self.serial_port.flush()
                
                self.logger.debug(f"发送语音指令: {content}")
                return True
                
        except serial.SerialException as e:
            self.logger.error(f"串口通信错误: {e}")
            # 尝试重连
            self.is_initialized = False
            return False
        except Exception as e:
            self.logger.error(f"语音播放失败: {e}")
            return False
            
    def stop(self):
        """停止播放 (ETV001-485 不支持直接停止正在播放的语音，除非发送空指令或特定控制指令)"""
        # 这里我们可以发送一个空指令或者静音指令，视具体需求而定
        # 目前简单实现为不做操作，因为硬件会自动播完
        pass
        
    def set_property(self, name: str, value: Any):
        """设置属性 (音量、语速等)"""
        # ETV001-485 支持通过指令设置音量等，但需要特定的指令格式
        # 例如: [v5] 设置音量
        # 这里暂时只记录日志，后续可根据需求实现指令封装
        self.logger.debug(f"设置属性 {name} = {value} (暂未通过硬件指令实现)")
        pass
        
    # --- 兼容 pyttsx3 接口 ---
    def say(self, text: str):
        """兼容 pyttsx3 的 say 方法"""
        return self.speak(text)
        
    def runAndWait(self):
        """兼容 pyttsx3 的 runAndWait 方法"""
        # 串口发送是同步的(write返回即发送完毕或进入缓冲区)，不需要额外的事件循环
        pass
        
    def cleanup(self):
        """清理资源"""
        with self.lock:
            if self.serial_port and self.serial_port.is_open:
                try:
                    self.serial_port.close()
                except Exception as e:
                    self.logger.error(f"关闭串口失败: {e}")
            self.is_initialized = False
            self.is_available = False
