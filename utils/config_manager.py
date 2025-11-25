#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 废弃物AI识别指导投放系统
提供配置文件的加载、验证、保存和管理功能
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, asdict


@dataclass
class CameraConfig:
    """摄像头配置"""
    device_id: int = 0
    resolution: Dict[str, int] = None
    fps: int = 30
    auto_focus: bool = True
    exposure: int = -1
    
    def __post_init__(self):
        if self.resolution is None:
            self.resolution = {"width": 1280, "height": 720}


@dataclass
class AIDetectionConfig:
    """AI检测配置"""
    model_path: str = "models/waste_detection.rknn"
    input_size: int = 640
    confidence_threshold: float = 0.6
    nms_threshold: float = 0.45
    max_detections: int = 10
    detection_interval: float = 0.1
    use_gpu: bool = False


@dataclass
class MotionDetectionConfig:
    """运动检测配置"""
    enable_motion_detection: bool = True  # 默认启用运动检测
    use_smart_detector: bool = True  # 使用智能检测器
    motion_threshold: int = 500
    min_contour_area: int = 1000
    detection_cooldown: float = 3.0
    recognition_cooldown: float = 5.0
    history: int = 500
    dist2_threshold: float = 400.0
    detect_shadows: bool = True
    blur_kernel_size: int = 5
    kernel_size: int = 3
    capture_delay: float = 1.0  # 延迟采集时间
    max_saved_images: int = 10  # 最大保存图片数量

    # 智能检测器专用配置
    roi_enabled: bool = True  # 启用ROI区域
    roi_top_ratio: float = 0.2  # ROI上边界比例
    roi_bottom_ratio: float = 0.8  # ROI下边界比例
    roi_left_ratio: float = 0.1  # ROI左边界比例
    roi_right_ratio: float = 0.9  # ROI右边界比例
    stability_threshold: float = 50  # 稳定性阈值
    min_stability_duration: float = 0.5  # 最小稳定时间
    max_stability_duration: float = 4.0  # 最大稳定时间
    min_presence_area: int = 3000  # 最小存在面积
    center_movement_threshold: float = 30  # 中心移动阈值
    min_presence_duration: float = 0.8  # 最小存在时间
    background_change_threshold: float = 0.1  # 背景变化阈值


@dataclass
class APIConfig:
    """API配置"""
    api_url: str = "https://api.openai.com/v1/chat/completions"
    api_key: str = ""
    model_name: str = "gpt-4-vision-preview"
    max_retries: int = 3
    timeout: int = 30


@dataclass
class UIConfig:
    """UI配置"""
    window_title: str = "废弃物AI识别指导投放系统"
    fullscreen: bool = False
    window_size: Dict[str, int] = None
    theme: str = "modern"
    language: str = "zh_CN"
    auto_hide_guidance: bool = True
    guidance_display_time: int = 5000
    
    def __post_init__(self):
        if self.window_size is None:
            self.window_size = {"width": 1024, "height": 768}


@dataclass
class AudioConfig:
    """音频配置"""
    enable_voice: bool = True
    voice_language: str = "zh"
    volume: float = 0.8
    speech_rate: int = 150


@dataclass
class LLMConfig:
    """大模型对话配置"""
    api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    api_key: str = ""
    model_name: str = "qwen-plus"
    max_retries: int = 3
    timeout: int = 30


@dataclass
class VoiceAssistantConfig:
    """语音助手配置"""
    enable_voice_assistant: bool = False
    wake_words: List[str] = None
    asr_engine: str = "speech_recognition_google"  # speech_recognition_google / offline_vosk
    asr_language: str = "zh-CN"
    max_listen_seconds: float = 6.0
    silence_timeout: float = 1.0
    response_with_tts: bool = True

    def __post_init__(self):
        if self.wake_words is None:
            self.wake_words = ["小蔚", "小蔚小蔚", "小卫"]


@dataclass
class IOControlConfig:
    """IO控制配置"""
    enable_io_control: bool = False
    ir_sensor_pin: int = 18
    detection_delay: float = 0.5
    detection_timeout: int = 10
    debounce_time: float = 0.1


@dataclass
class AnimationConfig:
    """动画配置"""
    enable_animations: bool = True
    particle_count: int = 20
    animation_duration: int = 3000
    success_animation_duration: int = 2000
    pulse_animation_fps: int = 20
    enable_animation_window: bool = False
    animation_window_always_on_top: bool = False
    gif_directory: str = "res/gif"


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file_path: str = "logs/waste_detection.log"
    max_file_size: str = "10MB"
    backup_count: int = 5
    console_output: bool = True


@dataclass
class DataConfig:
    """数据配置"""
    save_detection_results: bool = True
    save_images: bool = False
    data_path: str = "data/detection_results"
    max_data_age_days: int = 30


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_fps: int = 30
    processing_threads: int = 2
    buffer_size: int = 10
    memory_limit_mb: int = 1024


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.logger = logging.getLogger(__name__)
        self.config_dir = Path(config_dir)
        self.system_config_path = self.config_dir / "system_config.json"
        self.waste_config_path = self.config_dir / "waste_classification.json"
        
        # 配置数据
        self._system_config: Dict[str, Any] = {}
        self._waste_config: Dict[str, Any] = {}
        
        # 配置对象
        self._camera_config: Optional[CameraConfig] = None
        self._ai_detection_config: Optional[AIDetectionConfig] = None
        self._motion_detection_config: Optional[MotionDetectionConfig] = None
        self._api_config: Optional[APIConfig] = None
        self._ui_config: Optional[UIConfig] = None
        self._audio_config: Optional[AudioConfig] = None
        self._llm_config: Optional[LLMConfig] = None
        self._voice_assistant_config: Optional[VoiceAssistantConfig] = None
        self._io_control_config: Optional[IOControlConfig] = None
        self._animation_config: Optional[AnimationConfig] = None
        self._logging_config: Optional[LoggingConfig] = None
        self._data_config: Optional[DataConfig] = None
        self._performance_config: Optional[PerformanceConfig] = None
        
        # 初始化
        self._ensure_config_dir()
        self._load_configs()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"配置目录已创建: {self.config_dir}")
        except Exception as e:
            self.logger.error(f"创建配置目录失败: {e}")
            raise
    
    def _load_configs(self):
        """加载所有配置文件"""
        try:
            # 加载系统配置
            self._load_system_config()
            
            # 加载垃圾分类配置
            self._load_waste_config()
            
            # 解析配置对象
            self._parse_config_objects()
            
            self.logger.info("配置加载完成")
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            # 使用默认配置
            self._use_default_configs()
    
    def _load_system_config(self):
        """加载系统配置"""
        try:
            if self.system_config_path.exists():
                with open(self.system_config_path, 'r', encoding='utf-8') as f:
                    self._system_config = json.load(f)
                self.logger.info("系统配置加载成功")
            else:
                self.logger.warning("系统配置文件不存在，使用默认配置")
                self._system_config = self._get_default_system_config()
                self._save_system_config()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"系统配置文件格式错误: {e}")
            self._system_config = self._get_default_system_config()
            self._backup_and_recreate_config(self.system_config_path)
            
        except Exception as e:
            self.logger.error(f"加载系统配置失败: {e}")
            self._system_config = self._get_default_system_config()
    
    def _load_waste_config(self):
        """加载垃圾分类配置"""
        try:
            if self.waste_config_path.exists():
                with open(self.waste_config_path, 'r', encoding='utf-8') as f:
                    self._waste_config = json.load(f)
                self.logger.info("垃圾分类配置加载成功")
            else:
                self.logger.warning("垃圾分类配置文件不存在，使用默认配置")
                self._waste_config = self._get_default_waste_config()
                self._save_waste_config()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"垃圾分类配置文件格式错误: {e}")
            self._waste_config = self._get_default_waste_config()
            self._backup_and_recreate_config(self.waste_config_path)
            
        except Exception as e:
            self.logger.error(f"加载垃圾分类配置失败: {e}")
            self._waste_config = self._get_default_waste_config()
    
    def _parse_config_objects(self):
        """解析配置对象"""
        try:
            # 解析各个配置对象
            self._camera_config = CameraConfig(**self._system_config.get('camera', {}))
            self._ai_detection_config = AIDetectionConfig(**self._system_config.get('ai_detection', {}))
            self._motion_detection_config = MotionDetectionConfig(**self._system_config.get('motion_detection', {}))
            self._api_config = APIConfig(**self._system_config.get('api', {}))
            self._ui_config = UIConfig(**self._system_config.get('ui', {}))
            self._audio_config = AudioConfig(**self._system_config.get('audio', {}))
            self._llm_config = LLMConfig(**self._system_config.get('llm', {}))
            self._voice_assistant_config = VoiceAssistantConfig(**self._system_config.get('voice_assistant', {}))
            self._io_control_config = IOControlConfig(**self._system_config.get('io_control', {}))
            self._animation_config = AnimationConfig(**self._system_config.get('animation', {}))
            self._logging_config = LoggingConfig(**self._system_config.get('logging', {}))
            self._data_config = DataConfig(**self._system_config.get('data', {}))
            self._performance_config = PerformanceConfig(**self._system_config.get('performance', {}))
            
            self.logger.info("配置对象解析完成")
            
        except Exception as e:
            self.logger.error(f"配置对象解析失败: {e}")
            self._use_default_config_objects()
    
    def _use_default_configs(self):
        """使用默认配置"""
        self.logger.warning("使用默认配置")
        self._system_config = self._get_default_system_config()
        self._waste_config = self._get_default_waste_config()
        self._use_default_config_objects()
    
    def _use_default_config_objects(self):
        """使用默认配置对象"""
        self._camera_config = CameraConfig()
        self._ai_detection_config = AIDetectionConfig()
        self._motion_detection_config = MotionDetectionConfig()
        self._api_config = APIConfig()
        self._ui_config = UIConfig()
        self._audio_config = AudioConfig()
        self._llm_config = LLMConfig()
        self._voice_assistant_config = VoiceAssistantConfig()
        self._io_control_config = IOControlConfig()
        self._animation_config = AnimationConfig()
        self._logging_config = LoggingConfig()
        self._data_config = DataConfig()
        self._performance_config = PerformanceConfig()
    
    def _get_default_system_config(self) -> Dict[str, Any]:
        """获取默认系统配置"""
        return {
            "camera": asdict(CameraConfig()),
            "ai_detection": asdict(AIDetectionConfig()),
            "motion_detection": asdict(MotionDetectionConfig()),
            "api": asdict(APIConfig()),
            "ui": asdict(UIConfig()),
            "audio": asdict(AudioConfig()),
            "llm": asdict(LLMConfig()),
            "voice_assistant": asdict(VoiceAssistantConfig()),
            "io_control": asdict(IOControlConfig()),
            "animation": asdict(AnimationConfig()),
            "logging": asdict(LoggingConfig()),
            "data": asdict(DataConfig()),
            "performance": asdict(PerformanceConfig())
        }
    
    def _get_default_waste_config(self) -> Dict[str, Any]:
        """获取默认垃圾分类配置"""
        return {
            "waste_categories": {
                "可回收物": {
                    "color": "#0080ff",
                    "icon": "♻️",
                    "description": "可以回收利用的垃圾",
                    "guidance": "请清洗干净后投放到蓝色可回收物垃圾桶"
                },
                "有害垃圾": {
                    "color": "#ff0000",
                    "icon": "☠️",
                    "description": "对人体健康或环境有害的垃圾",
                    "guidance": "请投放到红色有害垃圾桶"
                },
                "湿垃圾": {
                    "color": "#8B4513",
                    "icon": "🥬",
                    "description": "易腐的生物质垃圾",
                    "guidance": "请投放到棕色湿垃圾桶"
                },
                "干垃圾": {
                    "color": "#808080",
                    "icon": "🗑️",
                    "description": "除有害垃圾、可回收物、湿垃圾以外的垃圾",
                    "guidance": "请投放到黑色干垃圾桶"
                }
            },
            "ai_model": {
                "classes": [
                    "plastic_bottle", "paper", "battery", "food_waste", "other"
                ],
                "class_mapping": {
                    "plastic_bottle": "可回收物",
                    "paper": "可回收物",
                    "battery": "有害垃圾",
                    "food_waste": "湿垃圾",
                    "other": "干垃圾"
                }
            }
        }
    
    def _backup_and_recreate_config(self, config_path: Path):
        """备份损坏的配置文件并重新创建"""
        try:
            backup_path = config_path.with_suffix('.json.backup')
            if config_path.exists():
                config_path.rename(backup_path)
                self.logger.info(f"已备份损坏的配置文件: {backup_path}")
            
            # 重新创建配置文件
            if config_path == self.system_config_path:
                self._save_system_config()
            elif config_path == self.waste_config_path:
                self._save_waste_config()
                
        except Exception as e:
            self.logger.error(f"备份配置文件失败: {e}")
    
    def _save_system_config(self):
        """保存系统配置"""
        try:
            with open(self.system_config_path, 'w', encoding='utf-8') as f:
                json.dump(self._system_config, f, indent=2, ensure_ascii=False)
            self.logger.info("系统配置保存成功")
        except Exception as e:
            self.logger.error(f"保存系统配置失败: {e}")
    
    def _save_waste_config(self):
        """保存垃圾分类配置"""
        try:
            with open(self.waste_config_path, 'w', encoding='utf-8') as f:
                json.dump(self._waste_config, f, indent=2, ensure_ascii=False)
            self.logger.info("垃圾分类配置保存成功")
        except Exception as e:
            self.logger.error(f"保存垃圾分类配置失败: {e}")
    
    # 配置访问方法
    def get_camera_config(self) -> CameraConfig:
        """获取摄像头配置"""
        return self._camera_config or CameraConfig()
    
    def get_ai_detection_config(self) -> AIDetectionConfig:
        """获取AI检测配置"""
        return self._ai_detection_config or AIDetectionConfig()
    
    def get_motion_detection_config(self) -> MotionDetectionConfig:
        """获取运动检测配置"""
        return self._motion_detection_config or MotionDetectionConfig()
    
    def get_api_config(self) -> APIConfig:
        """获取API配置"""
        return self._api_config or APIConfig()
    
    def get_ui_config(self) -> UIConfig:
        """获取UI配置"""
        return self._ui_config or UIConfig()
    
    def get_audio_config(self) -> AudioConfig:
        """获取音频配置"""
        return self._audio_config or AudioConfig()
    
    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        return self._llm_config or LLMConfig()

    def get_voice_assistant_config(self) -> VoiceAssistantConfig:
        """获取语音助手配置"""
        return self._voice_assistant_config or VoiceAssistantConfig()

    def get_io_config(self) -> IOControlConfig:
        """获取IO控制配置"""
        return self._io_control_config or IOControlConfig()
    
    def get_animation_config(self) -> AnimationConfig:
        """获取动画配置"""
        return self._animation_config or AnimationConfig()
    
    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        return self._logging_config or LoggingConfig()
    
    def get_data_config(self) -> DataConfig:
        """获取数据配置"""
        return self._data_config or DataConfig()
    
    def get_performance_config(self) -> PerformanceConfig:
        """获取性能配置"""
        return self._performance_config or PerformanceConfig()
    
    def get_waste_categories(self) -> Dict[str, Any]:
        """获取垃圾分类"""
        return self._waste_config.get('waste_categories', {})

    def get_waste_category_info(self, category: str) -> Optional[Dict[str, Any]]:
        """
        获取特定垃圾分类的信息

        Args:
            category: 垃圾分类名称（如：可回收物、有害垃圾等）

        Returns:
            分类信息字典，包含color、icon、description、items、guidance等
        """
        waste_categories = self.get_waste_categories()
        return waste_categories.get(category, None)
    
    def get_ai_model_config(self) -> Dict[str, Any]:
        """获取AI模型配置"""
        return self._waste_config.get('ai_model', {})
    
    def update_config(self, config_type: str, key: str, value: Any) -> bool:
        """
        更新配置 - 优化版本

        Args:
            config_type: 配置类型 ('system' 或 'waste')
            key: 配置键 (支持点分隔的嵌套键，如 'camera.fps')
            value: 配置值

        Returns:
            bool: 更新是否成功
        """
        # 输入验证
        if not isinstance(config_type, str) or config_type not in ['system', 'waste']:
            self.logger.error(f"无效的配置类型: {config_type}")
            return False

        if not isinstance(key, str) or not key.strip():
            self.logger.error("配置键不能为空")
            return False

        try:
            # 获取配置对象
            config = self._system_config if config_type == 'system' else self._waste_config

            # 备份原始值
            original_value = self._get_nested_value(config, key)

            # 验证新值
            if not self._validate_config_value(config_type, key, value):
                self.logger.error(f"配置值验证失败: {key} = {value}")
                return False

            # 处理嵌套键
            keys = key.split('.')
            current = config

            # 导航到目标位置
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                elif not isinstance(current[k], dict):
                    self.logger.error(f"配置路径冲突: {k} 不是字典类型")
                    return False
                current = current[k]

            # 设置值
            current[keys[-1]] = value

            # 保存配置
            try:
                if config_type == 'system':
                    self._save_system_config()
                    # 重新解析配置对象
                    self._parse_config_objects()
                else:
                    self._save_waste_config()

                self.logger.info(f"配置更新成功: {config_type}.{key} = {value}")
                return True

            except Exception as save_error:
                # 恢复原始值
                if original_value is not None:
                    current[keys[-1]] = original_value
                self.logger.error(f"保存配置失败，已恢复原值: {save_error}")
                return False

        except Exception as e:
            self.logger.error(f"更新配置失败: {e}")
            return False

    def _get_nested_value(self, config: dict, key: str) -> Any:
        """获取嵌套配置值"""
        try:
            keys = key.split('.')
            current = config
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return None
            return current
        except Exception:
            return None

    def _validate_config_value(self, config_type: str, key: str, value: Any) -> bool:
        """验证配置值的有效性"""
        try:
            # 基本类型检查
            if value is None:
                return False

            # 特定配置项的验证
            if config_type == 'system':
                if key.startswith('camera.'):
                    return self._validate_camera_config(key, value)
                elif key.startswith('ai_detection.'):
                    return self._validate_ai_config(key, value)
                elif key.startswith('performance.'):
                    return self._validate_performance_config(key, value)

            return True

        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            return False

    def _validate_camera_config(self, key: str, value: Any) -> bool:
        """验证摄像头配置"""
        if key == 'camera.fps' and (not isinstance(value, (int, float)) or value <= 0):
            return False
        if key == 'camera.device_id' and (not isinstance(value, int) or value < 0):
            return False
        return True

    def _validate_ai_config(self, key: str, value: Any) -> bool:
        """验证AI配置"""
        if key.endswith('_threshold') and (not isinstance(value, (int, float)) or not 0 <= value <= 1):
            return False
        return True

    def _validate_performance_config(self, key: str, value: Any) -> bool:
        """验证性能配置"""
        if key == 'performance.max_fps' and (not isinstance(value, (int, float)) or value <= 0):
            return False
        if key == 'performance.memory_limit_mb' and (not isinstance(value, int) or value <= 0):
            return False
        return True
    
    def validate_config(self) -> bool:
        """
        验证配置的有效性
        
        Returns:
            bool: 配置是否有效
        """
        try:
            is_valid = True
            
            # 验证摄像头配置
            camera_config = self.get_camera_config()
            if camera_config.fps <= 0 or camera_config.fps > 120:
                self.logger.warning(f"摄像头FPS配置异常: {camera_config.fps}")
                is_valid = False
            
            # 验证AI检测配置
            ai_config = self.get_ai_detection_config()
            if not (0.0 <= ai_config.confidence_threshold <= 1.0):
                self.logger.warning(f"置信度阈值配置异常: {ai_config.confidence_threshold}")
                is_valid = False
            
            # 验证API配置
            api_config = self.get_api_config()
            if api_config.timeout <= 0:
                self.logger.warning(f"API超时配置异常: {api_config.timeout}")
                is_valid = False
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"配置验证失败: {e}")
            return False
    
    def reload_configs(self):
        """重新加载配置"""
        try:
            self._load_configs()
            self.logger.info("配置重新加载完成")
        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例（单例模式）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager():
    """重置配置管理器（主要用于测试）"""
    global _config_manager
    _config_manager = None 