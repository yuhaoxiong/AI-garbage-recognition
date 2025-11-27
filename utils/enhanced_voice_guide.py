#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强语音指导模块 - 废弃物AI识别指导投放系统
提供多引擎支持、音频缓存、优先级队列等高级功能
"""

import os
import sys
import logging
import threading
import queue
import time
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass
from utils.config_manager import get_config_manager
from utils.voice_content_manager import get_voice_content_manager, VoiceContext, VoiceStyle
from utils.voice_engine_base import BaseVoiceEngine
from utils.serial_voice_engine import SerialVoiceEngine

# Linux TTS引擎支持
if sys.platform.startswith('linux'):
    try:
        from utils.linux_tts_engines import LinuxTTSManager
        LINUX_TTS_AVAILABLE = True
    except ImportError:
        LINUX_TTS_AVAILABLE = False
else:
    LINUX_TTS_AVAILABLE = False

# 语音调试支持
try:
    from utils.voice_debug import get_voice_debug_monitor
    VOICE_DEBUG_AVAILABLE = True
except ImportError:
    VOICE_DEBUG_AVAILABLE = False

# 尝试导入Qt信号支持
try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # 创建一个简单的信号模拟类
    class Signal:
        def __init__(self, *args):
            self.callbacks = []

        def connect(self, callback):
            self.callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in self.callbacks:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"信号回调失败: {e}")

    class QObject:
        pass

# 语音引擎可用性检查
TTS_ENGINES = {}

try:
    import pyttsx3
    TTS_ENGINES['pyttsx3'] = True
except ImportError:
    TTS_ENGINES['pyttsx3'] = False

try:
    import pygame
    TTS_ENGINES['pygame'] = True
except ImportError:
    TTS_ENGINES['pygame'] = False

# Windows SAPI检查
if sys.platform == 'win32':
    try:
        import win32com.client
        TTS_ENGINES['sapi'] = True
    except ImportError:
        TTS_ENGINES['sapi'] = False
else:
    TTS_ENGINES['sapi'] = False

# Linux espeak检查
if sys.platform.startswith('linux'):
    import subprocess
    try:
        subprocess.run(['espeak', '--version'], capture_output=True, check=True)
        TTS_ENGINES['espeak'] = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        TTS_ENGINES['espeak'] = False
else:
    TTS_ENGINES['espeak'] = False


class VoicePriority(Enum):
    """语音优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class VoiceEngineType(Enum):
    """语音引擎类型"""
    PYTTSX3 = "pyttsx3"
    SAPI = "sapi"
    ESPEAK = "espeak"
    PYGAME = "pygame"
    EDGE_TTS = "edge_tts"
    ESPEAK_NG = "espeak_ng"
    FESTIVAL = "festival"
    EKHO = "ekho"
    SERIAL = "serial"


@dataclass
class VoiceTask:
    """语音任务"""
    text: str
    priority: VoicePriority = VoicePriority.NORMAL
    callback: Optional[Callable] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def __lt__(self, other):
        """支持优先级队列比较"""
        if not isinstance(other, VoiceTask):
            return NotImplemented
        # 优先级数值越小，优先级越高
        return self.priority.value < other.priority.value


# BaseVoiceEngine 已移动到 utils/voice_engine_base.py 以避免循环导入


class Pyttsx3Engine(BaseVoiceEngine):
    """Pyttsx3语音引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None
        self.lock = threading.Lock()
    
    def initialize(self) -> bool:
        """初始化pyttsx3引擎"""
        try:
            if not TTS_ENGINES.get('pyttsx3', False):
                return False
            
            self.engine = pyttsx3.init()
            
            # 设置属性
            self.engine.setProperty('rate', self.config.get('speech_rate', 150))
            self.engine.setProperty('volume', self.config.get('volume', 0.8))
            
            # 设置中文语音
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Pyttsx3引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Pyttsx3引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            with self.lock:
                if not self.engine:
                    return False

                # 重新初始化引擎以避免线程问题
                try:
                    # 停止当前播放
                    self.engine.stop()

                    # 清空队列
                    self.engine.say(text)

                    # 尝试运行，设置超时保护
                    import threading
                    import time

                    def run_with_timeout():
                        try:
                            self.engine.runAndWait()
                        except Exception as e:
                            self.logger.error(f"runAndWait异常: {e}")

                    # 使用线程运行，避免无限阻塞
                    run_thread = threading.Thread(target=run_with_timeout, daemon=True)
                    run_thread.start()
                    run_thread.join(timeout=10.0)  # 最多等待10秒

                    if run_thread.is_alive():
                        self.logger.warning("runAndWait超时，使用估算时间")
                        time.sleep(len(text) * 0.08)

                except RuntimeError as e:
                    if "run loop already started" in str(e):
                        # 事件循环冲突，重新创建引擎实例
                        self.logger.warning("Pyttsx3事件循环冲突，重新初始化引擎")
                        try:
                            # 销毁旧引擎
                            del self.engine

                            # 创建新引擎
                            import pyttsx3
                            self.engine = pyttsx3.init()

                            # 重新设置属性
                            self.engine.setProperty('rate', self.config.get('speech_rate', 150))
                            self.engine.setProperty('volume', self.config.get('volume', 0.8))

                            # 设置中文语音
                            voices = self.engine.getProperty('voices')
                            for voice in voices:
                                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                                    self.engine.setProperty('voice', voice.id)
                                    break

                            # 重新播放
                            self.engine.say(text)
                            self.engine.runAndWait()

                        except Exception as reinit_error:
                            self.logger.error(f"重新初始化Pyttsx3引擎失败: {reinit_error}")
                            # 使用估算时间作为备用方案
                            time.sleep(len(text) * 0.08)
                    else:
                        raise

                return True

        except Exception as e:
            self.logger.error(f"Pyttsx3语音播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            if self.engine:
                self.engine.stop()
        except Exception as e:
            self.logger.error(f"停止Pyttsx3播放失败: {e}")
    
    def set_property(self, name: str, value: Any):
        """设置属性"""
        try:
            if self.engine:
                self.engine.setProperty(name, value)
        except Exception as e:
            self.logger.error(f"设置Pyttsx3属性失败: {e}")
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用声音"""
        try:
            if not self.engine:
                return []
            
            voices = []
            for voice in self.engine.getProperty('voices'):
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': getattr(voice, 'languages', [])
                })
            return voices
            
        except Exception as e:
            self.logger.error(f"获取Pyttsx3声音列表失败: {e}")
            return []
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.engine:
                self.engine.stop()
                del self.engine
                self.engine = None
        except Exception as e:
            self.logger.error(f"清理Pyttsx3资源失败: {e}")


class SAPIEngine(BaseVoiceEngine):
    """Windows SAPI语音引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sapi = None
    
    def initialize(self) -> bool:
        """初始化SAPI引擎"""
        try:
            if not TTS_ENGINES.get('sapi', False):
                return False
            
            import win32com.client
            self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
            
            # 设置语速和音量
            speech_rate = self.config.get('speech_rate', 150)
            self.sapi.Rate = self._convert_rate(speech_rate)  # SAPI使用-10到10的范围
            self.sapi.Volume = int(self.config.get('volume', 0.8) * 100)  # SAPI使用0-100
            self.config['speech_rate'] = speech_rate

            self.is_available = True
            self.is_initialized = True
            self.logger.info("SAPI引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"SAPI引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            if not self.sapi:
                return False

            # 使用同步播放，但在单独线程中运行以避免阻塞主工作线程
            import threading
            import time

            def speak_in_thread():
                try:
                    # 0表示同步播放，会等待播放完成
                    self.sapi.Speak(text, 0)
                except Exception as e:
                    self.logger.error(f"SAPI线程播放失败: {e}")

            # 在单独线程中播放
            speak_thread = threading.Thread(target=speak_in_thread, daemon=True)
            speak_thread.start()

            # 等待播放完成，设置合理的超时时间
            max_wait_time = len(text) * 0.15 + 3  # 根据文本长度估算等待时间
            speak_thread.join(timeout=max_wait_time)

            # 如果线程还在运行，说明可能卡住了
            if speak_thread.is_alive():
                self.logger.warning(f"SAPI播放超时，文本: {text[:20]}...")
                # 使用估算时间作为备用
                time.sleep(len(text) * 0.08)

            return True

        except Exception as e:
            self.logger.error(f"SAPI语音播放失败: {e}")
            # 尝试重新初始化SAPI
            try:
                import win32com.client
                self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
                self.sapi.Rate = self.config.get('speech_rate', 0)
                self.sapi.Volume = int(self.config.get('volume', 0.8) * 100)

                # 重新尝试播放
                self.sapi.Speak(text, 1)
                time.sleep(len(text) * 0.08)  # 使用估算时间

                self.logger.info("SAPI引擎重新初始化成功")
                return True
            except Exception as reinit_error:
                self.logger.error(f"SAPI引擎重新初始化失败: {reinit_error}")
                return False
    
    def stop(self):
        """停止播放"""
        try:
            if self.sapi:
                self.sapi.Speak("", 2)  # 2表示立即停止
        except Exception as e:
            self.logger.error(f"停止SAPI播放失败: {e}")
    
    def set_property(self, name: str, value: Any):
        """设置属性"""
        try:
            if not self.sapi:
                return

            if name == 'rate':
                # 转换为SAPI范围
                self.sapi.Rate = self._convert_rate(value)
                self.config['speech_rate'] = value
            elif name == 'volume':
                self.sapi.Volume = int(max(0, min(1, value)) * 100)
                self.config['volume'] = value

        except Exception as e:
            self.logger.error(f"设置SAPI属性失败: {e}")

    @staticmethod
    def _convert_rate(value: Any) -> int:
        """将通用语速（约50-300）映射到SAPI的-10~10范围"""
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 150
        normalized = int(round((numeric - 150) / 15))
        return max(-10, min(10, normalized))
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用声音"""
        try:
            if not self.sapi:
                return []

            voices = []
            voice_tokens = self.sapi.GetVoices()
            for i in range(voice_tokens.Count):
                voice = voice_tokens.Item(i)
                voices.append({
                    'id': voice.Id,
                    'name': voice.GetDescription(),
                    'languages': []
                })
            return voices

        except Exception as e:
            self.logger.error(f"获取SAPI声音列表失败: {e}")
            return []


class VoiceStatus(Enum):
    """语音状态"""
    IDLE = "idle"
    SPEAKING = "speaking"
    PAUSED = "paused"
    ERROR = "error"


class VoiceMonitor(QObject):
    """语音状态监控器"""

    # 信号定义
    status_changed = Signal(str)  # 状态变化
    task_started = Signal(dict)   # 任务开始
    task_completed = Signal(dict, bool)  # 任务完成
    task_failed = Signal(dict, str)  # 任务失败
    queue_updated = Signal(int)   # 队列更新
    engine_changed = Signal(str)  # 引擎切换

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.VoiceMonitor")

    def emit_status_changed(self, status: VoiceStatus):
        """发送状态变化信号"""
        self.status_changed.emit(status.value)

    def emit_task_started(self, task: VoiceTask):
        """发送任务开始信号"""
        task_info = {
            'text': task.text,
            'priority': task.priority.name,
            'timestamp': task.timestamp,
            'metadata': task.metadata
        }
        self.task_started.emit(task_info)

    def emit_task_completed(self, task: VoiceTask, success: bool):
        """发送任务完成信号"""
        task_info = {
            'text': task.text,
            'priority': task.priority.name,
            'timestamp': task.timestamp,
            'metadata': task.metadata,
            'duration': time.time() - task.timestamp
        }
        self.task_completed.emit(task_info, success)

    def emit_task_failed(self, task: VoiceTask, error: str):
        """发送任务失败信号"""
        task_info = {
            'text': task.text,
            'priority': task.priority.name,
            'timestamp': task.timestamp,
            'metadata': task.metadata
        }
        self.task_failed.emit(task_info, error)

    def emit_queue_updated(self, size: int):
        """发送队列更新信号"""
        self.queue_updated.emit(size)

    def emit_engine_changed(self, engine_name: str):
        """发送引擎切换信号"""
        self.engine_changed.emit(engine_name)


class EnhancedVoiceGuide(QObject):
    """增强语音指导类"""

    def __init__(self):
        super().__init__()
        """初始化增强语音指导"""
        self.config_manager = get_config_manager()
        self.content_manager = get_voice_content_manager()
        self.logger = logging.getLogger(__name__)

        # 配置加载
        try:
            audio_config = self.config_manager.get_audio_config()
            self.enabled = audio_config.enable_voice
            self.language = audio_config.voice_language
            self.volume = audio_config.volume
            self.rate = audio_config.speech_rate
        except Exception as e:
            self.logger.error(f"加载音频配置失败: {e}")
            self.enabled = True
            self.language = 'zh'
            self.volume = 0.8
            self.rate = 150

        # 语音引擎管理
        self.engines = {}
        self.current_engine = None
        self.linux_tts_manager = None
        
        # 根据平台设置引擎优先级
        if sys.platform == 'win32':
            # Windows优先使用SAPI
            self.engine_priority = [
                VoiceEngineType.SAPI,
                VoiceEngineType.PYTTSX3,
                VoiceEngineType.ESPEAK
            ]
        elif sys.platform.startswith('linux'):
            # Linux优先使用高质量TTS引擎
            self.engine_priority = [
                VoiceEngineType.EDGE_TTS,
                VoiceEngineType.EKHO,
                VoiceEngineType.ESPEAK_NG,
                VoiceEngineType.PYTTSX3,
                VoiceEngineType.FESTIVAL,
                VoiceEngineType.ESPEAK
            ]
        else:
            # 其他平台
            self.engine_priority = [
                VoiceEngineType.PYTTSX3,
                VoiceEngineType.ESPEAK,
                VoiceEngineType.SAPI
            ]

        # 优先级队列
        self.voice_queue = queue.PriorityQueue()
        self.queue_lock = threading.Lock()

        # 工作线程
        self.worker_thread = None
        self.worker_running = False

        # 音频缓存
        self.cache_dir = Path("cache/audio")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.audio_cache = {}

        # 状态监控
        self.monitor = VoiceMonitor()
        self.current_task = None
        self.current_status = VoiceStatus.IDLE
        self.last_error = None
        self.statistics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_speaking_time': 0.0,
            'engine_switches': 0
        }

        # 初始化
        self._init_engines()
        if self.enabled:
            self._start_worker()

    def _init_engines(self):
        """初始化语音引擎"""
        config = {
            'volume': self.volume,
            'speech_rate': self.rate,
            'language': self.language
        }

        # 1. 优先检查串口语音配置
        try:
            audio_config = self.config_manager.get_audio_config()
            serial_config = getattr(audio_config, 'serial_voice', None)
            
            # 兼容字典配置
            if not serial_config:
                system_config = getattr(self.config_manager, 'config', {})
                if not system_config:
                    system_config = getattr(self.config_manager, '_system_config', {})
                
                audio_dict = system_config.get('audio', {})
                serial_dict = audio_dict.get('serial_voice', {})
                if serial_dict.get('enable'):
                    serial_config = serial_dict

            if serial_config and (isinstance(serial_config, dict) and serial_config.get('enable') or getattr(serial_config, 'enable', False)):
                try:
                    config_dict = serial_config if isinstance(serial_config, dict) else serial_config.__dict__
                    serial_engine = SerialVoiceEngine(config_dict)
                    if serial_engine.initialize():
                        self.engines[VoiceEngineType.SERIAL] = serial_engine
                        self.current_engine = VoiceEngineType.SERIAL
                        self.logger.info("使用串口语音引擎 (优先级最高)")
                        # 如果串口语音启用且成功，可以跳过其他引擎初始化，或者作为备用
                        # 这里我们将其加入优先级列表的最前面
                        self.engine_priority.insert(0, VoiceEngineType.SERIAL)
                except Exception as e:
                    self.logger.error(f"初始化串口语音引擎失败: {e}")
        except Exception as e:
            self.logger.error(f"检查串口语音配置失败: {e}")

        # 在Linux系统上，优先初始化Linux TTS管理器
        if sys.platform.startswith('linux') and LINUX_TTS_AVAILABLE:
            try:
                self.linux_tts_manager = LinuxTTSManager(config)
                linux_engines = self.linux_tts_manager.get_available_engines()
                
                # 将Linux TTS引擎添加到可用引擎列表
                for engine_name in linux_engines:
                    engine_type = VoiceEngineType(engine_name)
                    linux_engine = self.linux_tts_manager.get_engine(engine_name)
                    if linux_engine:
                        self.engines[engine_type] = linux_engine
                        if self.current_engine is None:
                            self.current_engine = engine_type
                            self.logger.info(f"使用Linux TTS引擎: {engine_type.value}")
                
                # 如果有可用的Linux引擎，记录安装建议
                recommendations = self.linux_tts_manager.install_recommendations()
                if recommendations:
                    self.logger.info("可安装更多TTS引擎以获得更好效果:")
                    for engine, cmd in recommendations.items():
                        self.logger.info(f"  {engine}: {cmd}")
                        
            except Exception as e:
                self.logger.error(f"初始化Linux TTS管理器失败: {e}")

        # 按优先级初始化传统引擎
        for engine_type in self.engine_priority:
            # 跳过已经通过Linux TTS管理器初始化的引擎
            if engine_type in self.engines:
                continue
                
            try:
                if engine_type == VoiceEngineType.PYTTSX3:
                    engine = Pyttsx3Engine(config)
                elif engine_type == VoiceEngineType.SAPI:
                    engine = SAPIEngine(config)
                elif engine_type == VoiceEngineType.ESPEAK:
                    engine = EspeakEngine(config)
                else:
                    continue

                if engine.initialize():
                    self.engines[engine_type] = engine
                    if self.current_engine is None:
                        self.current_engine = engine_type
                        self.logger.info(f"使用语音引擎: {engine_type.value}")

            except Exception as e:
                self.logger.error(f"初始化引擎 {engine_type.value} 失败: {e}")

        if not self.engines:
            self.logger.warning("没有可用的语音引擎")
            self.enabled = False
        else:
            self.logger.info(f"已初始化 {len(self.engines)} 个语音引擎: {[e.value for e in self.engines.keys()]}")

    def _start_worker(self):
        """启动工作线程"""
        if self.worker_running:
            return

        self.worker_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("语音工作线程已启动")

    def _worker_loop(self):
        """工作线程主循环"""
        while self.worker_running:
            try:
                # 获取任务（阻塞等待，超时1秒）
                try:
                    priority, task = self.voice_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # 执行任务
                self.current_task = task
                self._set_status(VoiceStatus.SPEAKING)
                self.monitor.emit_task_started(task)
                self.statistics['total_tasks'] += 1

                start_time = time.time()
                self.logger.debug(f"开始执行语音任务: {task.text[:20]}...")

                try:
                    success = self._execute_task(task)
                    duration = time.time() - start_time
                    self.logger.debug(f"任务执行完成: {success}, 耗时: {duration:.2f}s")
                except Exception as task_error:
                    success = False
                    duration = time.time() - start_time
                    self.logger.error(f"任务执行异常: {task_error}")
                    self.last_error = str(task_error)

                # 更新统计
                if success:
                    self.statistics['successful_tasks'] += 1
                    self.statistics['total_speaking_time'] += duration
                    self.monitor.emit_task_completed(task, True)
                else:
                    self.statistics['failed_tasks'] += 1
                    self.monitor.emit_task_failed(task, self.last_error or "未知错误")

                # 任务完成回调
                if task.callback:
                    try:
                        task.callback(success, task)
                    except Exception as e:
                        self.logger.error(f"任务回调失败: {e}")

                self.current_task = None
                self._set_status(VoiceStatus.IDLE)
                self.voice_queue.task_done()
                self.monitor.emit_queue_updated(self.voice_queue.qsize())

            except Exception as e:
                self.logger.error(f"语音工作线程异常: {e}")
                self.last_error = str(e)
                self._set_status(VoiceStatus.ERROR)
                time.sleep(0.1)

    def _set_status(self, status: VoiceStatus):
        """设置状态"""
        if self.current_status != status:
            self.current_status = status
            self.monitor.emit_status_changed(status)

    def _execute_task(self, task: VoiceTask) -> bool:
        """执行语音任务"""
        try:
            # 检查缓存
            cache_key = self._get_cache_key(task.text)
            cached_file = self.cache_dir / f"{cache_key}.wav"

            if cached_file.exists() and TTS_ENGINES.get('pygame', False):
                # 使用缓存的音频文件
                self.logger.debug(f"使用缓存音频: {task.text}")
                return self._play_cached_audio(cached_file)
            else:
                # 使用TTS引擎并尝试缓存
                success = self._speak_with_engine(task.text)
                if success:
                    # 尝试生成缓存文件
                    self._generate_cache_file(task.text, cache_key)
                return success

        except Exception as e:
            self.logger.error(f"执行语音任务失败: {e}")
            return False

    def _generate_cache_file(self, text: str, cache_key: str):
        """生成音频缓存文件"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.wav"

            # 如果已存在则跳过
            if cache_file.exists():
                return

            # 仅当当前引擎确为Pyttsx3时才生成wav缓存，避免Linux下混用不同TTS导致杂音/音色跳变
            if self.current_engine == VoiceEngineType.PYTTSX3 and VoiceEngineType.PYTTSX3 in self.engines:
                engine = self.engines[VoiceEngineType.PYTTSX3]
                if hasattr(engine.engine, 'save_to_file'):
                    engine.engine.save_to_file(text, str(cache_file))
                    engine.engine.runAndWait()
                    self.logger.debug(f"生成缓存文件: {cache_file}")

            # 清理过期缓存
            self._cleanup_cache()

        except Exception as e:
            self.logger.debug(f"生成缓存文件失败: {e}")

    def _cleanup_cache(self):
        """清理过期缓存文件"""
        try:
            # 获取所有缓存文件
            cache_files = list(self.cache_dir.glob("*.wav"))

            # 如果缓存文件过多，删除最旧的
            max_cache_files = 100
            if len(cache_files) > max_cache_files:
                # 按修改时间排序
                cache_files.sort(key=lambda f: f.stat().st_mtime)

                # 删除最旧的文件
                for old_file in cache_files[:-max_cache_files]:
                    try:
                        old_file.unlink()
                        self.logger.debug(f"删除过期缓存: {old_file}")
                    except Exception as e:
                        self.logger.debug(f"删除缓存文件失败: {e}")

            # 删除超过7天的缓存文件
            current_time = time.time()
            max_age = 7 * 24 * 3600  # 7天

            for cache_file in cache_files:
                try:
                    if current_time - cache_file.stat().st_mtime > max_age:
                        cache_file.unlink()
                        self.logger.debug(f"删除过期缓存: {cache_file}")
                except Exception as e:
                    self.logger.debug(f"删除过期缓存失败: {e}")

        except Exception as e:
            self.logger.debug(f"清理缓存失败: {e}")

    def clear_cache(self):
        """清空所有缓存"""
        try:
            for cache_file in self.cache_dir.glob("*.wav"):
                cache_file.unlink()
            self.logger.info("已清空语音缓存")
        except Exception as e:
            self.logger.error(f"清空缓存失败: {e}")

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            cache_files = list(self.cache_dir.glob("*.wav"))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                'cache_dir': str(self.cache_dir),
                'file_count': len(cache_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'oldest_file': min(cache_files, key=lambda f: f.stat().st_mtime).name if cache_files else None,
                'newest_file': max(cache_files, key=lambda f: f.stat().st_mtime).name if cache_files else None
            }
        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {e}")
            return {'error': str(e)}

    def _speak_with_engine(self, text: str) -> bool:
        """使用TTS引擎播放语音"""
        if not self.current_engine or self.current_engine not in self.engines:
            return False

        engine = self.engines[self.current_engine]
        success = engine.speak(text)

        # 如果当前引擎失败，尝试其他引擎
        if not success:
            for engine_type, engine_obj in self.engines.items():
                if engine_type != self.current_engine:
                    self.logger.info(f"尝试备用引擎: {engine_type.value}")
                    if engine_obj.speak(text):
                        old_engine = self.current_engine.value if self.current_engine else "None"
                        self.current_engine = engine_type
                        self.statistics['engine_switches'] += 1
                        self.monitor.emit_engine_changed(engine_type.value)
                        self.logger.info(f"引擎切换: {old_engine} -> {engine_type.value}")
                        return True

            self.logger.error("所有语音引擎都失败了")
            return False

        return True

    def _play_cached_audio(self, audio_file: Path) -> bool:
        """播放缓存的音频文件"""
        try:
            import pygame
            # 仅在未初始化时按统一参数初始化，避免频繁re-init导致噪声
            if not pygame.mixer.get_init():
                try:
                    # 统一采样参数（与Edge-TTS默认24k单声道更接近），较大的buffer降低卡顿与爆音
                    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
                except Exception:
                    pygame.mixer.init()

            # 停止任何可能残留的播放，避免叠加导致杂音
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

            pygame.mixer.music.load(str(audio_file))
            # 设置音量并淡入，减少起始“哒/啪”声
            try:
                pygame.mixer.music.set_volume(float(self.volume))
            except Exception:
                pass
            pygame.mixer.music.play(fade_ms=50)
            

            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            return True

        except Exception as e:
            self.logger.error(f"播放缓存音频失败: {e}")
            return False

    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        content = f"{text}_{self.language}_{self.rate}_{self.volume}"
        return hashlib.md5(content.encode()).hexdigest()

    def speak(self, text: str, priority: VoicePriority = VoicePriority.NORMAL,
              callback: Optional[Callable] = None, metadata: Optional[Dict] = None):
        """添加语音任务到队列"""
        if not self.enabled or not text.strip():
            return

        # 调试监控
        if VOICE_DEBUG_AVAILABLE:
            try:
                debug_monitor = get_voice_debug_monitor()
                source = metadata.get('source', 'EnhancedVoiceGuide') if metadata else 'EnhancedVoiceGuide'
                debug_monitor.log_voice_call(text.strip(), source, priority.name.lower())
            except Exception as e:
                self.logger.debug(f"语音调试监控失败: {e}")

        task = VoiceTask(
            text=text.strip(),
            priority=priority,
            callback=callback,
            metadata=metadata or {}
        )

        try:
            # 优先级队列：数值越小优先级越高，添加时间戳确保唯一性
            priority_value = (5 - priority.value, task.timestamp)
            self.voice_queue.put((priority_value, task), timeout=1.0)
            self.logger.debug(f"语音任务已加入队列: {text} (优先级: {priority.name})")

        except queue.Full:
            self.logger.warning("语音队列已满，跳过任务")
        except Exception as e:
            self.logger.error(f"添加语音任务失败: {e}")

    def speak_urgent(self, text: str, callback: Optional[Callable] = None):
        """播放紧急语音（最高优先级）"""
        self.speak(text, VoicePriority.URGENT, callback)

    def speak_guidance(
        self,
        waste_category: str,
        specific_item: Optional[str] = None,
        composition: Optional[str] = None,
        degradation_time: Optional[str] = None,
        recycling_value: Optional[str] = None,
        guidance_text: str = None,
        priority: VoicePriority = VoicePriority.HIGH
    ):
        """播放垃圾投放指导语音"""
        if guidance_text:
            text = guidance_text
        else:
            # 使用内容管理器获取指导文本
            text = self.content_manager.get_guidance_text(
                waste_category,
                specific_item=specific_item,
                composition=composition,
                degradation_time=degradation_time,
                recycling_value=recycling_value
            )

        metadata = {
            'type': 'guidance',
            'category': waste_category,
            'specific_item': specific_item,
            'composition': composition,
            'degradation_time': degradation_time,
            'recycling_value': recycling_value
        }

        self.speak(text, priority, metadata=metadata)

    def speak_welcome(self, priority: VoicePriority = VoicePriority.NORMAL):
        """播放欢迎语音"""
        text = self.content_manager.get_voice_text(VoiceContext.WELCOME)
        self.speak(text, priority, metadata={'type': 'welcome'})

    def speak_detection_start(self, priority: VoicePriority = VoicePriority.NORMAL):
        """播放检测开始语音"""
        text = self.content_manager.get_voice_text(VoiceContext.DETECTION_START)
        self.speak(text, priority, metadata={'type': 'detection_start'})

    def speak_detection_progress(self, priority: VoicePriority = VoicePriority.NORMAL):
        """播放检测进行中语音"""
        text = self.content_manager.get_voice_text(VoiceContext.DETECTION_PROGRESS)
        self.speak(text, priority, metadata={'type': 'detection_progress'})

    def speak_detection_success(
        self,
        category: str,
        specific_item: Optional[str] = None,
        priority: VoicePriority = VoicePriority.HIGH
    ):
        """播放检测成功语音"""
        main_category = category.split('-')[0] if '-' in category else category
        if specific_item:
            text = f"识别成功，检测到{specific_item}，属于{main_category}。"
        else:
            text = f"识别成功，检测到{main_category}。"

        metadata = {
            'type': 'detection_success',
            'category': category,
            'specific_item': specific_item
        }
        self.speak(text, priority, metadata=metadata)

    def speak_detection_failed(self, priority: VoicePriority = VoicePriority.HIGH):
        """播放检测失败语音"""
        text = self.content_manager.get_voice_text(VoiceContext.DETECTION_FAILED)
        self.speak(text, priority, metadata={'type': 'detection_failed'})

    def speak_thank_you(self, priority: VoicePriority = VoicePriority.NORMAL):
        """播放感谢语音"""
        text = self.content_manager.get_voice_text(VoiceContext.THANK_YOU)
        self.speak(text, priority, metadata={'type': 'thank_you'})

    def speak_error(self, error_message: str = None, priority: VoicePriority = VoicePriority.HIGH):
        """播放错误语音"""
        if error_message:
            text = error_message
        else:
            text = self.content_manager.get_voice_text(VoiceContext.ERROR)
        self.speak(text, priority, metadata={'type': 'error'})

    def set_voice_style(self, style: VoiceStyle):
        """设置语音风格"""
        self.content_manager.set_style(style)
        self.logger.info(f"语音风格已设置为: {style.value}")

    def set_voice_language(self, language: str):
        """设置语音语言"""
        self.content_manager.set_language(language)
        self.logger.info(f"语音语言已设置为: {language}")

    def update_audio_settings(self, volume: Optional[float] = None, speech_rate: Optional[int] = None):
        """更新音频播放的音量与语速"""
        try:
            volume_changed = volume is not None and abs(volume - self.volume) > 1e-3
            rate_changed = speech_rate is not None and speech_rate != self.rate

            if not (volume_changed or rate_changed):
                return

            if volume is not None:
                self.volume = max(0.0, min(1.0, float(volume)))
            if speech_rate is not None:
                self.rate = int(speech_rate)

            for engine in self.engines.values():
                if not engine or not getattr(engine, "is_initialized", False):
                    continue
                if volume is not None:
                    engine.config["volume"] = self.volume
                    try:
                        engine.set_property("volume", self.volume)
                    except Exception as e:
                        self.logger.debug(f"更新引擎音量失败: {e}")
                if speech_rate is not None:
                    engine.config["speech_rate"] = self.rate
                    try:
                        engine.set_property("rate", self.rate)
                    except Exception as e:
                        self.logger.debug(f"更新引擎语速失败: {e}")

        except Exception as e:
            self.logger.error(f"更新语音设置失败: {e}")

    def update_voice_preferences(self, preferences: Dict[str, Any]):
        """更新语音个性化偏好"""
        self.content_manager.update_preferences(preferences)
        self.logger.info("语音偏好已更新")

    def interrupt_current(self):
        """打断当前播放"""
        try:
            if self.current_engine and self.current_engine in self.engines:
                self.engines[self.current_engine].stop()

            # 清空队列中的普通优先级任务
            with self.queue_lock:
                temp_queue = queue.PriorityQueue()
                while not self.voice_queue.empty():
                    try:
                        priority, task = self.voice_queue.get_nowait()
                        # 只保留高优先级和紧急任务
                        if task.priority in [VoicePriority.HIGH, VoicePriority.URGENT]:
                            temp_queue.put((priority, task))
                    except queue.Empty:
                        break

                self.voice_queue = temp_queue

            self.logger.info("已打断当前语音播放")

        except Exception as e:
            self.logger.error(f"打断语音播放失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        """获取语音系统状态"""
        return {
            'enabled': self.enabled,
            'status': self.current_status.value,
            'current_engine': self.current_engine.value if self.current_engine else None,
            'available_engines': [engine.value for engine in self.engines.keys()],
            'queue_size': self.voice_queue.qsize(),
            'current_task': {
                'text': self.current_task.text if self.current_task else None,
                'priority': self.current_task.priority.name if self.current_task else None,
                'duration': time.time() - self.current_task.timestamp if self.current_task else None
            } if self.current_task else None,
            'last_error': self.last_error,
            'statistics': self.statistics.copy(),
            'cache_info': self.get_cache_info()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        stats = self.statistics.copy()
        if stats['total_tasks'] > 0:
            stats['success_rate'] = stats['successful_tasks'] / stats['total_tasks']
            stats['average_speaking_time'] = stats['total_speaking_time'] / stats['successful_tasks'] if stats['successful_tasks'] > 0 else 0
        else:
            stats['success_rate'] = 0
            stats['average_speaking_time'] = 0

        return stats

    def reset_statistics(self):
        """重置统计信息"""
        self.statistics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_speaking_time': 0.0,
            'engine_switches': 0
        }
        self.logger.info("语音统计信息已重置")

    def cleanup(self):
        """清理资源"""
        try:
            # 停止工作线程
            self.worker_running = False
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=2.0)

            # 清理引擎
            for engine in self.engines.values():
                engine.cleanup()

            self.logger.info("语音系统资源已清理")

        except Exception as e:
            self.logger.error(f"清理语音系统资源失败: {e}")


# 全局实例
_enhanced_voice_guide = None

def get_enhanced_voice_guide() -> EnhancedVoiceGuide:
    """获取增强语音指导实例"""
    global _enhanced_voice_guide
    if _enhanced_voice_guide is None:
        _enhanced_voice_guide = EnhancedVoiceGuide()
    return _enhanced_voice_guide


class EspeakEngine(BaseVoiceEngine):
    """Linux espeak语音引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.process = None
    
    def initialize(self) -> bool:
        """初始化espeak引擎"""
        try:
            if not TTS_ENGINES.get('espeak', False):
                return False
            
            # 测试espeak是否可用
            import subprocess
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True, check=True)
            
            self.is_available = True
            self.is_initialized = True
            self.logger.info("Espeak引擎初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Espeak引擎初始化失败: {e}")
            return False
    
    def speak(self, text: str) -> bool:
        """播放语音"""
        try:
            import subprocess
            
            # 构建espeak命令
            cmd = [
                'espeak',
                '-v', 'zh',  # 中文语音
                '-s', str(self.config.get('speech_rate', 150)),  # 语速
                '-a', str(int(self.config.get('volume', 0.8) * 200)),  # 音量
                text
            ]
            
            # 执行命令
            subprocess.run(cmd, check=True)
            return True
            
        except Exception as e:
            self.logger.error(f"Espeak语音播放失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
        except Exception as e:
            self.logger.error(f"停止Espeak播放失败: {e}")
    
    def set_property(self, name: str, value: Any):
        """设置属性"""
        # espeak通过命令行参数设置，这里只更新配置
        if name in ['rate', 'volume']:
            self.config[name] = value
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用声音"""
        try:
            import subprocess
            result = subprocess.run(['espeak', '--voices'], 
                                  capture_output=True, text=True, check=True)
            
            voices = []
            for line in result.stdout.split('\n')[1:]:  # 跳过标题行
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        voices.append({
                            'id': parts[1],
                            'name': ' '.join(parts[3:]),
                            'languages': [parts[1]]
                        })
            return voices
            
        except Exception as e:
            self.logger.error(f"获取Espeak声音列表失败: {e}")
            return []
