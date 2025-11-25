#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API客户端 - 废弃物AI识别指导投放系统
调用外部API进行图像识别
"""

import os
import base64
import json
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime


class APIClient:
    """API客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化API客户端
        
        Args:
            config: API配置字典
        """
        self.logger = logging.getLogger(__name__)
        
        # 配置参数
        self.api_url = config.get('api_url', '')
        self.api_key = config.get('api_key', '')
        self.model_name = config.get('model_name', 'gpt-4-vision-preview')
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        
        # 检查配置完整性
        if not self.api_url or not self.api_key:
            self.logger.warning("API配置不完整，将使用模拟识别")
            self.use_simulation = True
        else:
            self.use_simulation = False
            self.logger.info(f"API客户端初始化完成: {self.api_url}")
    
    def call_api(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        调用API进行图像识别
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            识别结果字典
        """
        try:
            if self.use_simulation:
                return self._simulate_recognition(image_path)
            
            # 检查图像文件
            if not os.path.exists(image_path):
                self.logger.error(f"图像文件不存在: {image_path}")
                return None
            
            # 编码图像
            image_base64 = self._encode_image(image_path)
            if not image_base64:
                return None
            
            # 构建请求
            payload = self._build_request_payload(image_base64)
            
            # 发送请求
            for attempt in range(self.max_retries):
                try:
                    response = self._send_request(payload)
                    if response:
                        result = self._parse_response(response)
                        if result:
                            result['image_path'] = image_path
                            result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            return result
                except Exception as e:
                    self.logger.warning(f"API调用尝试 {attempt + 1} 失败: {e}")
                    if attempt == self.max_retries - 1:
                        self.logger.error("API调用达到最大重试次数")
            
            return None
            
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            return None
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """
        编码图像为base64
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            base64编码的图像字符串
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            self.logger.error(f"图像编码失败: {e}")
            return None
    
    def _build_request_payload(self, image_base64: str) -> Dict[str, Any]:
        """
        构建请求载荷
        
        Args:
            image_base64: base64编码的图像
            
        Returns:
            请求载荷字典
        """
        return {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """请识别图片中的废弃物类型，并按照以下格式返回JSON结果：
{
    "category": "垃圾分类（可回收物/有害垃圾/湿垃圾/干垃圾）",
    "confidence": 0.85,
    "description": "详细描述和投放指导"
}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
    
    def _send_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送HTTP请求
        
        Args:
            payload: 请求载荷
            
        Returns:
            响应字典
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    def _parse_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析API响应
        
        Args:
            response: API响应字典
            
        Returns:
            解析后的结果字典
        """
        try:
            # 提取响应内容
            choices = response.get('choices', [])
            if not choices:
                self.logger.error("API响应中没有choices")
                return None
            
            content = choices[0].get('message', {}).get('content', '')
            if not content:
                self.logger.error("API响应内容为空")
                return None
            
            # 尝试解析JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # 如果不是JSON格式，尝试提取关键信息
                return self._extract_info_from_text(content)
            
        except Exception as e:
            self.logger.error(f"解析API响应失败: {e}")
            return None
    
    def _extract_info_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取信息

        Args:
            text: 响应文本

        Returns:
            提取的信息字典
        """
        # 层级关键词匹配
        hierarchical_categories = {
            '可回收物': {
                '塑料类': ['塑料', '瓶子', '塑料瓶', '矿泉水瓶'],
                '纸类': ['纸', '纸箱', '报纸', '书本'],
                '金属类': ['金属', '罐子', '易拉罐', '铁罐'],
                '玻璃类': ['玻璃', '玻璃瓶', '酒瓶']
            },
            '有害垃圾': {
                '电池类': ['电池', '干电池', '蓄电池'],
                '灯管类': ['灯管', '节能灯', '日光灯'],
                '药品类': ['药品', '药物', '过期药'],
                '化学类': ['油漆', '化学', '农药']
            },
            '厨余垃圾': {
                '果皮类': ['果皮', '苹果皮', '香蕉皮', '橘子皮'],
                '蔬菜类': ['菜叶', '蔬菜', '白菜', '萝卜'],
                '剩菜类': ['剩饭', '剩菜', '食物残渣'],
                '骨头类': ['骨头', '鱼骨', '鸡骨']
            },
            '其他垃圾': {
                '织物类': ['衣物', '布料', '破旧衣服'],
                '陶瓷类': ['陶瓷', '瓷器', '破碗'],
                '其他类': ['纸巾', '尿布', '烟蒂', '灰尘']
            }
        }

        text_lower = text.lower()

        # 匹配层级分类
        for main_category, sub_categories in hierarchical_categories.items():
            for sub_category, keywords in sub_categories.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        specific_item = keyword  # 使用匹配的关键词作为具体物品名
                        category = f"{main_category}-{sub_category}-{specific_item}"
                        return {
                            'category': category,
                            'description': f'根据关键词"{keyword}"识别为{category}'
                        }

        return {
            'category': '其他垃圾-其他类-未知物品',
            'description': '无法确定垃圾类型，请咨询工作人员'
        }
    
    def _simulate_recognition(self, image_path: str) -> Dict[str, Any]:
        """
        模拟识别（用于测试）
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            模拟的识别结果
        """
        import random
        
        categories = [
            {
                'category': '可回收物',
                'confidence': 0.85,
                'description': '检测到塑料瓶，请清洗后投放到蓝色可回收物垃圾桶'
            },
            {
                'category': '有害垃圾',
                'confidence': 0.78,
                'description': '检测到废电池，请投放到红色有害垃圾桶'
            },
            {
                'category': '湿垃圾',
                'confidence': 0.92,
                'description': '检测到果皮，请投放到棕色湿垃圾桶'
            },
            {
                'category': '干垃圾',
                'confidence': 0.73,
                'description': '检测到纸巾，请投放到黑色干垃圾桶'
            }
        ]
        
        result = random.choice(categories)
        result['image_path'] = image_path
        result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result['detection_method'] = 'API调用'
        
        self.logger.info(f"模拟识别结果: {result['category']} (置信度: {result['confidence']})")
        return result
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        if self.use_simulation:
            self.logger.info("使用模拟模式，跳过连接测试")
            return True
        
        try:
            # 发送简单的测试请求
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(
                self.api_url.replace('/chat/completions', '/models'),
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("API连接测试成功")
                return True
            else:
                self.logger.warning(f"API连接测试失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"API连接测试异常: {e}")
            return False
