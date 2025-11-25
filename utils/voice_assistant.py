#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音助手 - 支持“唤醒词 + 语音问答（LLM）”
默认唤醒词：小蔚 / 小蔚小蔚
ASR优先使用 speech_recognition (在线/系统麦克风)，可选Vosk离线识别
"""

import logging
import threading
import queue
import time
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal

from utils.config_manager import get_config_manager
from utils.llm_client import get_llm_client


class VoiceAssistantWorker(QObject):
    """语音助手工作器（线程内运行）"""

    wakeup_state_changed = Signal(bool)  # True: 唤醒中/监听问题, False: 未唤醒
    status_changed = Signal(str)
    asr_text_ready = Signal(str)
    reply_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self.llm = get_llm_client()

        self._load_config()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._queue: "queue.Queue[str]" = queue.Queue()

        # 可选依赖
        try:
            import speech_recognition as sr  # noqa
            self._sr_available = True
        except Exception:
            self._sr_available = False
        try:
            import vosk  # noqa
            self._vosk_available = True
        except Exception:
            self._vosk_available = False

    def _load_config(self):
        cfg = self.config_manager.get_voice_assistant_config()
        self.enabled = bool(cfg.enable_voice_assistant)
        self.wake_words = [w.strip() for w in (cfg.wake_words or []) if w.strip()]
        self.asr_engine = cfg.asr_engine
        self.asr_language = cfg.asr_language
        self.max_listen_seconds = float(cfg.max_listen_seconds)
        self.silence_timeout = float(cfg.silence_timeout)
        self.response_with_tts = bool(cfg.response_with_tts)

    def start(self):
        if not self.enabled:
            self.logger.info("语音助手在配置中未启用，跳过启动")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.status_changed.emit("语音助手已启动，等待唤醒词…")

    def stop(self):
        try:
            self._stop_event.set()
        except Exception:
            pass

    def _run_loop(self):
        self.logger.info("VoiceAssistantWorker 线程启动")
        # 主循环：先等待唤醒词，再录音识别问题，调用LLM，回复
        while not self._stop_event.is_set():
            try:
                if not self._wait_for_wake_word():
                    break
                self.wakeup_state_changed.emit(True)
                question = self._listen_user_question()
                if question:
                    self.asr_text_ready.emit(question)
                    reply = self._ask_llm(question)
                    self.reply_ready.emit(reply)
                    # 交给上层播放TTS，或在这里播放
                else:
                    self.status_changed.emit("未识别到问题，请重试")
                # 进入未唤醒状态
                self.wakeup_state_changed.emit(False)

            except Exception as e:
                self.logger.error(f"语音助手循环异常: {e}")
                time.sleep(0.5)

        self.logger.info("VoiceAssistantWorker 线程结束")

    # === 关键步骤 ===
    def _wait_for_wake_word(self) -> bool:
        """持续用ASR低功耗监听短语，遇到唤醒词则返回True。"""
        self.status_changed.emit("等待唤醒词：" + "/".join(self.wake_words))
        if self.asr_engine.startswith("speech_recognition") and self._sr_available:
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.8)
                    while not self._stop_event.is_set():
                        self.status_changed.emit("请说：小蔚 小蔚…")
                        audio = r.listen(source, phrase_time_limit=3)
                        try:
                            text = r.recognize_google(audio, language=self.asr_language)
                            text = (text or "").strip()
                            if text:
                                self.logger.info(f"监听到语音: {text}")
                                for w in self.wake_words:
                                    if w in text:
                                        self.status_changed.emit("已唤醒，请提问…")
                                        return True
                        except Exception:
                            pass
            except Exception as e:
                self.logger.error(f"唤醒监听失败: {e}")
                time.sleep(1.0)
                return False
        elif self.asr_engine == "offline_vosk" and self._vosk_available:
            # 简化：此处可扩展Vosk关键字识别，当前返回False作为占位
            self.logger.warning("Vosk关键字监听未实现，将回退到离线整句识别")
            return False
        else:
            self.logger.warning("ASR引擎不可用，无法语音唤醒")
            return False

        return False

    def _listen_user_question(self) -> Optional[str]:
        """在唤醒后短时间内收听用户问题并转文字"""
        if self.asr_engine.startswith("speech_recognition") and self._sr_available:
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    self.status_changed.emit("请说出你的问题…")
                    audio = r.listen(source, timeout=self.silence_timeout, phrase_time_limit=self.max_listen_seconds)
                try:
                    text = r.recognize_google(audio, language=self.asr_language)
                    return text.strip()
                except Exception as e:
                    self.logger.warning(f"ASR识别失败: {e}")
                    return None
            except Exception as e:
                self.logger.error(f"录音失败: {e}")
                return None

        # Vosk 可在此实现
        return None

    def _ask_llm(self, user_text: str) -> str:
        try:
            messages = [
                {"role": "system", "content": "你是垃圾分类助手，请简短回答用户问题，并给出所属垃圾分类。"},
                {"role": "user", "content": user_text}
            ]
            reply = self.llm.chat(messages)
            return reply
        except Exception as e:
            self.logger.error(f"LLM对话失败: {e}")
            return "抱歉，我暂时无法回答。"


