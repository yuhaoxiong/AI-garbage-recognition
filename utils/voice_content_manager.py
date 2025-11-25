#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音内容管理器 - 废弃物AI识别指导投放系统
提供多语言、个性化、情景化的语音内容管理
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class VoiceStyle(Enum):
    """语音风格"""
    FORMAL = "formal"           # 正式
    FRIENDLY = "friendly"       # 友好
    ENCOURAGING = "encouraging" # 鼓励
    URGENT = "urgent"          # 紧急


class VoiceContext(Enum):
    """语音场景"""
    WELCOME = "welcome"                 # 欢迎
    DETECTION_START = "detection_start" # 开始检测
    DETECTION_PROGRESS = "detection_progress" # 检测进行中
    DETECTION_SUCCESS = "detection_success"   # 检测成功
    DETECTION_FAILED = "detection_failed"     # 检测失败
    GUIDANCE = "guidance"               # 投放指导
    THANK_YOU = "thank_you"            # 感谢
    ERROR = "error"                    # 错误
    MAINTENANCE = "maintenance"         # 维护


@dataclass
class VoiceTemplate:
    """语音模板"""
    text: str
    style: VoiceStyle
    context: VoiceContext
    language: str = "zh"
    variables: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []


class VoiceContentManager:
    """语音内容管理器"""
    
    def __init__(self, content_file: str = "config/voice_content.json"):
        self.logger = logging.getLogger(__name__)
        self.content_file = Path(content_file)
        
        # 语音内容库
        self.templates: Dict[str, Dict[str, List[VoiceTemplate]]] = {}
        self.waste_categories: Dict[str, Dict[str, Any]] = {}
        
        # 当前设置
        self.current_language = "zh"
        self.current_style = VoiceStyle.FRIENDLY
        self.personalization_enabled = True
        
        # 个性化设置
        self.user_preferences = {
            'use_encouragement': True,
            'use_humor': False,
            'verbosity_level': 'normal',  # simple, normal, detailed
            'use_statistics': True
        }
        
        # 加载内容
        self._load_content()
        self._init_default_content()
    
    def _load_content(self):
        """加载语音内容"""
        try:
            if self.content_file.exists():
                with open(self.content_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载模板
                if 'templates' in data:
                    for lang, contexts in data['templates'].items():
                        self.templates[lang] = {}
                        for context, styles in contexts.items():
                            self.templates[lang][context] = []
                            for style, templates in styles.items():
                                for template_data in templates:
                                    template = VoiceTemplate(
                                        text=template_data['text'],
                                        style=VoiceStyle(style),
                                        context=VoiceContext(context),
                                        language=lang,
                                        variables=template_data.get('variables', [])
                                    )
                                    self.templates[lang][context].append(template)
                
                # 加载垃圾分类信息
                if 'waste_categories' in data:
                    self.waste_categories = data['waste_categories']
                
                self.logger.info("语音内容加载成功")
                
        except Exception as e:
            self.logger.error(f"加载语音内容失败: {e}")
            self._init_default_content()
    
    def _init_default_content(self):
        """初始化默认语音内容"""
        if not self.templates:
            self.templates = {
                'zh': {
                    'welcome': [],
                    'detection_start': [],
                    'detection_progress': [],
                    'detection_success': [],
                    'detection_failed': [],
                    'guidance': [],
                    'thank_you': [],
                    'error': [],
                    'maintenance': []
                }
            }
        
        # 添加默认中文模板
        default_templates = [
            # 欢迎语音
            VoiceTemplate("欢迎使用智能垃圾分类系统，请将废弃物放在检测区域", VoiceStyle.FRIENDLY, VoiceContext.WELCOME),
            VoiceTemplate("您好！我是您的垃圾分类小助手，让我们一起保护环境吧", VoiceStyle.ENCOURAGING, VoiceContext.WELCOME),
            
            # 检测开始
            VoiceTemplate("检测到物体，正在分析中，请稍候", VoiceStyle.FORMAL, VoiceContext.DETECTION_START),
            VoiceTemplate("发现新物品！让我看看这是什么", VoiceStyle.FRIENDLY, VoiceContext.DETECTION_START),
            
            # 检测进行中
            VoiceTemplate("正在识别中，请保持物品稳定", VoiceStyle.FORMAL, VoiceContext.DETECTION_PROGRESS),
            VoiceTemplate("马上就好，请稍等片刻", VoiceStyle.FRIENDLY, VoiceContext.DETECTION_PROGRESS),
            
            # 检测成功
            VoiceTemplate("识别完成！这是{category}", VoiceStyle.FORMAL, VoiceContext.DETECTION_SUCCESS, variables=['category']),
            VoiceTemplate("太棒了！我认出这是{category}", VoiceStyle.ENCOURAGING, VoiceContext.DETECTION_SUCCESS, variables=['category']),
            
            # 投放指导
            VoiceTemplate("请将{category}投放到{bin_color}垃圾桶", VoiceStyle.FORMAL, VoiceContext.GUIDANCE, variables=['category', 'bin_color']),
            VoiceTemplate("{category}应该放入{bin_color}垃圾桶哦", VoiceStyle.FRIENDLY, VoiceContext.GUIDANCE, variables=['category', 'bin_color']),
            
            # 感谢
            VoiceTemplate("谢谢您的配合，垃圾分类从我做起", VoiceStyle.FORMAL, VoiceContext.THANK_YOU),
            VoiceTemplate("做得很好！您为环保做出了贡献", VoiceStyle.ENCOURAGING, VoiceContext.THANK_YOU),
            
            # 检测失败
            VoiceTemplate("抱歉，无法识别此物品，请咨询工作人员", VoiceStyle.FORMAL, VoiceContext.DETECTION_FAILED),
            VoiceTemplate("这个有点难倒我了，建议询问现场工作人员", VoiceStyle.FRIENDLY, VoiceContext.DETECTION_FAILED),
            
            # 错误
            VoiceTemplate("系统出现错误，请稍后重试", VoiceStyle.FORMAL, VoiceContext.ERROR),
            VoiceTemplate("哎呀，出了点小问题，请重新尝试", VoiceStyle.FRIENDLY, VoiceContext.ERROR),
        ]
        
        # 添加到模板库
        for template in default_templates:
            context_key = template.context.value
            if context_key not in self.templates['zh']:
                self.templates['zh'][context_key] = []
            self.templates['zh'][context_key].append(template)
        
        # 默认垃圾分类信息
        if not self.waste_categories:
            self.waste_categories = {
                '可回收物': {
                    'bin_color': '蓝色',
                    'guidance': '请清洗干净后投放到蓝色可回收物垃圾桶',
                    'encouragement': '很好！回收利用能减少资源浪费'
                },
                '有害垃圾': {
                    'bin_color': '红色',
                    'guidance': '请小心投放到红色有害垃圾桶，避免破损',
                    'encouragement': '谢谢您的细心处理，保护环境人人有责'
                },
                '湿垃圾': {
                    'bin_color': '棕色',
                    'guidance': '请沥干水分后投放到棕色湿垃圾桶',
                    'encouragement': '湿垃圾可以变成有机肥料，真是太棒了'
                },
                '干垃圾': {
                    'bin_color': '黑色',
                    'guidance': '请投放到黑色干垃圾桶',
                    'encouragement': '正确分类让垃圾处理更高效'
                }
            }
    
    def get_voice_text(self, context: VoiceContext, **kwargs) -> str:
        """获取语音文本"""
        try:
            # 获取当前语言和场景的模板
            lang_templates = self.templates.get(self.current_language, {})
            context_templates = lang_templates.get(context.value, [])
            
            if not context_templates:
                return self._get_fallback_text(context, **kwargs)
            
            # 根据风格筛选模板
            style_templates = [t for t in context_templates if t.style == self.current_style]
            if not style_templates:
                style_templates = context_templates
            
            # 随机选择一个模板
            template = random.choice(style_templates)
            
            # 替换变量
            text = template.text
            for var_name, var_value in kwargs.items():
                text = text.replace(f'{{{var_name}}}', str(var_value))
            
            # 应用个性化
            if self.personalization_enabled:
                text = self._apply_personalization(text, context, **kwargs)
            
            return text
            
        except Exception as e:
            self.logger.error(f"获取语音文本失败: {e}")
            return self._get_fallback_text(context, **kwargs)
    
    def _get_fallback_text(self, context: VoiceContext, **kwargs) -> str:
        """获取备用文本"""
        fallback_texts = {
            VoiceContext.WELCOME: "欢迎使用智能垃圾分类系统",
            VoiceContext.DETECTION_START: "正在检测中",
            VoiceContext.DETECTION_PROGRESS: "请稍候",
            VoiceContext.DETECTION_SUCCESS: f"识别完成：{kwargs.get('category', '未知物品')}",
            VoiceContext.GUIDANCE: f"请按照指导投放{kwargs.get('category', '物品')}",
            VoiceContext.THANK_YOU: "谢谢您的配合",
            VoiceContext.DETECTION_FAILED: "识别失败，请重试",
            VoiceContext.ERROR: "系统错误",
            VoiceContext.MAINTENANCE: "系统维护中"
        }
        return fallback_texts.get(context, "系统提示")
    
    def _apply_personalization(self, text: str, context: VoiceContext, **kwargs) -> str:
        """应用个性化设置"""
        try:
            # 添加鼓励语句
            if (self.user_preferences.get('use_encouragement', True) and 
                context in [VoiceContext.DETECTION_SUCCESS, VoiceContext.THANK_YOU]):
                
                category = kwargs.get('category')
                if category and category in self.waste_categories:
                    encouragement = self.waste_categories[category].get('encouragement')
                    if encouragement:
                        text += f"。{encouragement}"
            
            # 添加统计信息
            if (self.user_preferences.get('use_statistics', True) and 
                context == VoiceContext.THANK_YOU):
                # 这里可以添加统计信息，如"今天已正确分类X件垃圾"
                pass
            
            # 根据详细程度调整
            verbosity = self.user_preferences.get('verbosity_level', 'normal')
            if verbosity == 'simple':
                # 简化文本
                text = text.split('。')[0]  # 只取第一句
            elif verbosity == 'detailed':
                # 添加详细信息
                category = kwargs.get('category')
                if category and category in self.waste_categories:
                    guidance = self.waste_categories[category].get('guidance')
                    if guidance and context == VoiceContext.DETECTION_SUCCESS:
                        text += f"。{guidance}"
            
            return text
            
        except Exception as e:
            self.logger.error(f"应用个性化设置失败: {e}")
            return text
    
    def get_guidance_text(
        self,
        category: str,
        specific_item: Optional[str] = None,
        composition: Optional[str] = None,
        degradation_time: Optional[str] = None,
        recycling_value: Optional[str] = None
    ) -> str:
        """获取投放指导文本"""
        try:
            category_key = category.split('-')[0] if '-' in category else category
            category_info = self.waste_categories.get(category_key, {})
            bin_color = category_info.get('bin_color', '对应')
            
            # 构建基础指导文本
            kwargs = {
                'category': category_key,
                'bin_color': bin_color
            }

            base_text = self.get_voice_text(VoiceContext.GUIDANCE, **kwargs)

            detail_sentences: List[str] = []
            if specific_item:
                detail_sentences.append(f"检测物品为{specific_item}。")
            if composition:
                detail_sentences.append(f"主要成分包括{composition}。")
            if degradation_time:
                detail_sentences.append(f"在自然环境中大约需要{degradation_time}才能降解。")
            if recycling_value:
                detail_sentences.append(f"回收与处理建议：{recycling_value}。")

            detail_sentences.append(base_text)

            return " ".join(detail_sentences)
            
        except Exception as e:
            self.logger.error(f"获取指导文本失败: {e}")
            return f"请将{category_key}投放到对应垃圾桶"
    
    def set_language(self, language: str):
        """设置语言"""
        if language in self.templates:
            self.current_language = language
            self.logger.info(f"语言已切换到: {language}")
        else:
            self.logger.warning(f"不支持的语言: {language}")
    
    def set_style(self, style: VoiceStyle):
        """设置语音风格"""
        self.current_style = style
        self.logger.info(f"语音风格已切换到: {style.value}")
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """更新个性化偏好"""
        self.user_preferences.update(preferences)
        self.logger.info("个性化偏好已更新")
    
    def save_content(self):
        """保存语音内容到文件"""
        try:
            # 准备数据
            data = {
                'templates': {},
                'waste_categories': self.waste_categories
            }
            
            # 转换模板数据
            for lang, contexts in self.templates.items():
                data['templates'][lang] = {}
                for context, templates in contexts.items():
                    data['templates'][lang][context] = {}
                    for template in templates:
                        style_key = template.style.value
                        if style_key not in data['templates'][lang][context]:
                            data['templates'][lang][context][style_key] = []
                        
                        data['templates'][lang][context][style_key].append({
                            'text': template.text,
                            'variables': template.variables
                        })
            
            # 保存到文件
            self.content_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.content_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("语音内容已保存")
            
        except Exception as e:
            self.logger.error(f"保存语音内容失败: {e}")


# 全局实例
_voice_content_manager = None

def get_voice_content_manager() -> VoiceContentManager:
    """获取语音内容管理器实例"""
    global _voice_content_manager
    if _voice_content_manager is None:
        _voice_content_manager = VoiceContentManager()
    return _voice_content_manager
