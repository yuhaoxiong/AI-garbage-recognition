#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音集成模块 - 废弃物AI识别指导投放系统
提供原有VoiceGuide类的兼容接口，同时集成增强语音功能
"""

import logging
from typing import Optional, Dict, Any, Callable
from utils.enhanced_voice_guide import get_enhanced_voice_guide, VoicePriority, VoiceStyle
from utils.voice_content_manager import VoiceContext
from utils.config_manager import get_config_manager


class VoiceGuideCompat:
    """语音指导兼容类 - 保持与原有接口的兼容性"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enhanced_guide = get_enhanced_voice_guide()
        self.config_manager = get_config_manager()
        
        # 兼容性标志
        self.enabled = self.enhanced_guide.enabled
        self._last_volume = getattr(self.enhanced_guide, "volume", 0.8)
        self._last_rate = getattr(self.enhanced_guide, "rate", 150)
        
        # 连接增强语音的信号到兼容回调
        if hasattr(self.enhanced_guide, 'monitor'):
            self.enhanced_guide.monitor.status_changed.connect(self._on_status_changed)
            self.enhanced_guide.monitor.task_completed.connect(self._on_task_completed)
            self.enhanced_guide.monitor.task_failed.connect(self._on_task_failed)
        
        self.logger.info("语音指导兼容层已初始化")
    
    def _on_status_changed(self, status: str):
        """状态变化回调"""
        self.logger.debug(f"语音状态变化: {status}")
    
    def _on_task_completed(self, task_info: Dict[str, Any], success: bool):
        """任务完成回调"""
        if success:
            self.logger.debug(f"语音任务完成: {task_info.get('text', '')[:20]}...")
        else:
            self.logger.warning(f"语音任务失败: {task_info.get('text', '')[:20]}...")
    
    def _on_task_failed(self, task_info: Dict[str, Any], error: str):
        """任务失败回调"""
        self.logger.error(f"语音任务失败: {error}")

    # === 原有接口兼容方法 ===

    def _refresh_audio_settings(self):
        """从配置中心刷新语音播放参数"""
        try:
            audio_config = self.config_manager.get_audio_config()
        except Exception as e:
            self.logger.debug(f"获取音频配置失败，保持现状: {e}")
            return

        if audio_config.enable_voice != self.enabled:
            self.enabled = audio_config.enable_voice
            self.enhanced_guide.enabled = self.enabled

        volume = audio_config.volume
        rate = audio_config.speech_rate

        volume_changed = abs(volume - self._last_volume) > 1e-3
        rate_changed = rate != self._last_rate

        if volume_changed or rate_changed:
            self.enhanced_guide.update_audio_settings(
                volume=volume if volume_changed else None,
                speech_rate=rate if rate_changed else None
            )
            self._last_volume = volume
            self._last_rate = rate
    
    def speak(self, text: str, priority: str = "normal", callback: Optional[Callable] = None, source: str = "VoiceGuideCompat"):
        """播放语音 - 兼容原有接口"""
        try:
            self._refresh_audio_settings()
            if not self.enabled:
                self.logger.debug("语音功能已禁用，跳过播放请求")
                return

            # 转换优先级
            voice_priority = self._convert_priority(priority)
            
            # 添加source信息到metadata
            metadata = {'source': source}
            
            # 调用增强语音
            self.enhanced_guide.speak(text, voice_priority, callback, metadata)
            
        except Exception as e:
            self.logger.error(f"语音播放失败: {e}")
    
    def speak_guidance(
        self,
        waste_category: str,
        specific_item: str = None,
        composition: str = None,
        degradation_time: str = None,
        recycling_value: str = None,
        guidance_text: str = None
    ):
        """播放投放指导 - 兼容原有接口"""
        try:
            self._refresh_audio_settings()
            if not self.enabled:
                self.logger.debug("语音功能已禁用，跳过投放指导播放")
                return

            self.enhanced_guide.speak_guidance(
                waste_category,
                specific_item=specific_item,
                composition=composition,
                degradation_time=degradation_time,
                recycling_value=recycling_value,
                guidance_text=guidance_text
            )
        except Exception as e:
            self.logger.error(f"指导语音播放失败: {e}")
    
    def stop_current(self):
        """停止当前播放 - 兼容原有接口"""
        try:
            self.enhanced_guide.interrupt_current()
        except Exception as e:
            self.logger.error(f"停止语音失败: {e}")
    
    def is_speaking(self) -> bool:
        """检查是否正在播放 - 兼容原有接口"""
        try:
            status = self.enhanced_guide.get_status()
            return status.get('status') == 'speaking'
        except Exception as e:
            self.logger.error(f"获取播放状态失败: {e}")
            return False
    
    def set_enabled(self, enabled: bool):
        """设置启用状态 - 兼容原有接口"""
        self.enabled = enabled
        self.enhanced_guide.enabled = enabled
        self.logger.info(f"语音功能已{'启用' if enabled else '禁用'}")
    
    def cleanup(self):
        """清理资源 - 兼容原有接口"""
        try:
            self.enhanced_guide.cleanup()
        except Exception as e:
            self.logger.error(f"清理语音资源失败: {e}")
    
    # === 增强功能接口 ===
    
    def speak_welcome(self):
        """播放欢迎语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过欢迎语音")
            return
        self.enhanced_guide.speak_welcome()

    def speak_detection_start(self):
        """播放检测开始语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过检测开始语音")
            return
        self.enhanced_guide.speak_detection_start()

    def speak_detection_progress(self):
        """播放检测进行中语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过检测进度语音")
            return
        self.enhanced_guide.speak_detection_progress()

    def speak_detection_success(self, category: str, specific_item: str = None):
        """播放检测成功语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过检测成功语音")
            return
        self.enhanced_guide.speak_detection_success(category, specific_item=specific_item)

    def speak_detection_failed(self):
        """播放检测失败语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过检测失败语音")
            return
        self.enhanced_guide.speak_detection_failed()

    def speak_thank_you(self):
        """播放感谢语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过感谢语音")
            return
        self.enhanced_guide.speak_thank_you()

    def speak_error(self, error_message: str = None):
        """播放错误语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过错误提示语音")
            return
        self.enhanced_guide.speak_error(error_message)

    def speak_urgent(self, text: str):
        """播放紧急语音"""
        self._refresh_audio_settings()
        if not self.enabled:
            self.logger.debug("语音功能已禁用，跳过紧急语音")
            return
        self.enhanced_guide.speak_urgent(text)
    
    def set_voice_style(self, style: str):
        """设置语音风格"""
        try:
            voice_style = VoiceStyle(style.lower())
            self.enhanced_guide.set_voice_style(voice_style)
        except ValueError:
            self.logger.warning(f"不支持的语音风格: {style}")
    
    def set_voice_language(self, language: str):
        """设置语音语言"""
        self.enhanced_guide.set_voice_language(language)
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """更新语音偏好"""
        self.enhanced_guide.update_voice_preferences(preferences)
    
    def get_status(self) -> Dict[str, Any]:
        """获取语音系统状态"""
        return self.enhanced_guide.get_status()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取语音统计信息"""
        return self.enhanced_guide.get_statistics()
    
    def clear_cache(self):
        """清空语音缓存"""
        self.enhanced_guide.clear_cache()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return self.enhanced_guide.get_cache_info()
    
    # === 工具方法 ===
    
    def _convert_priority(self, priority: str) -> VoicePriority:
        """转换优先级字符串到枚举"""
        priority_map = {
            'low': VoicePriority.LOW,
            'normal': VoicePriority.NORMAL,
            'high': VoicePriority.HIGH,
            'urgent': VoicePriority.URGENT
        }
        return priority_map.get(priority.lower(), VoicePriority.NORMAL)


class VoiceIntegrationManager:
    """语音集成管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.voice_guide = VoiceGuideCompat()
        
        # 场景语音映射
        self.scene_voice_map = {
            'system_start': self._on_system_start,
            'motion_detected': self._on_motion_detected,
            'image_captured': self._on_image_captured,
            'recognition_success': self._on_recognition_success,
            'recognition_failed': self._on_recognition_failed,
            'guidance_complete': self._on_guidance_complete,
            'system_error': self._on_system_error,
            'system_shutdown': self._on_system_shutdown
        }
        
        self.logger.info("语音集成管理器已初始化")
    
    def handle_scene(self, scene: str, **kwargs):
        """处理场景语音"""
        try:
            if scene in self.scene_voice_map:
                self.scene_voice_map[scene](**kwargs)
            else:
                self.logger.warning(f"未知场景: {scene}")
        except Exception as e:
            self.logger.error(f"处理场景语音失败 {scene}: {e}")
    
    def _on_system_start(self, **kwargs):
        """系统启动"""
        self.voice_guide.speak_welcome()
    
    def _on_motion_detected(self, **kwargs):
        """检测到运动"""
        self.voice_guide.speak_detection_start()
    
    def _on_image_captured(self, **kwargs):
        """图片已捕获"""
        self.voice_guide.speak_detection_progress()
    
    def _on_recognition_success(
        self,
        category: str = None,
        specific_item: str = None,
        composition: str = None,
        degradation_time: str = None,
        recycling_value: str = None,
        **kwargs
    ):
        """识别成功"""
        if category:
            self.voice_guide.speak_detection_success(category, specific_item=specific_item)
            # 延迟播放指导语音
            import threading
            def delayed_guidance():
                import time
                time.sleep(1.5)  # 等待1.5秒，确保前一个语音播放完成
                self.voice_guide.speak_guidance(
                    category,
                    specific_item=specific_item,
                    composition=composition,
                    degradation_time=degradation_time,
                    recycling_value=recycling_value
                )
            
            threading.Thread(target=delayed_guidance, daemon=True).start()
    
    def _on_recognition_failed(self, **kwargs):
        """识别失败"""
        self.voice_guide.speak_detection_failed()
    
    def _on_guidance_complete(self, **kwargs):
        """指导完成"""
        self.voice_guide.speak_thank_you()
    
    def _on_system_error(self, error_message: str = None, **kwargs):
        """系统错误"""
        self.voice_guide.speak_error(error_message)
    
    def _on_system_shutdown(self, **kwargs):
        """系统关闭"""
        self.voice_guide.speak("系统即将关闭，感谢使用", priority="high")
    
    def get_voice_guide(self) -> VoiceGuideCompat:
        """获取语音指导实例"""
        return self.voice_guide
    
    def cleanup(self):
        """清理资源"""
        self.voice_guide.cleanup()


# 全局实例
_voice_integration_manager = None
_voice_guide_instance = None

def get_voice_integration_manager() -> VoiceIntegrationManager:
    """获取语音集成管理器实例"""
    global _voice_integration_manager
    if _voice_integration_manager is None:
        _voice_integration_manager = VoiceIntegrationManager()
    return _voice_integration_manager

def get_voice_guide() -> VoiceGuideCompat:
    """获取语音指导实例 - 兼容原有接口（单例模式）"""
    global _voice_guide_instance
    if _voice_guide_instance is None:
        _voice_guide_instance = get_voice_integration_manager().get_voice_guide()
    return _voice_guide_instance
