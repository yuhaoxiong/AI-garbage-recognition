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
                            result.setdefault('detection_method', 'API调用')
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
                            "text": """请识别图片中的物品，不要回答未获取到，并严格按照以下 JSON 格式返回信息：
{
    "category": "垃圾分类-细分类-具体物品名称",
    "composition": "垃圾的主要组成成分",
    "degradation_time": "该垃圾在自然环境中的大致降解时间",
    "recycling_value": "垃圾的回收利用价值与处理建议"
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

            # 打印原始JSON文本，便于排查格式问题
            self.logger.debug("API原始JSON文本: %s", content)

            # 尝试解析JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                self.logger.error("API原始JSON文本: %s", content)
                self.logger.error("API响应不是有效的JSON格式")
                return self._default_result()

            return self._normalize_result(result)

        except Exception as e:
            self.logger.error(f"解析API响应失败: {e}")
            return None
    
    def _normalize_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化模型返回的数据结构，确保字段完整。
        """
        category = str(data.get('category', '')).strip()
        if not category:
            category = '其他垃圾-其他类-未知物品'
        elif category.count('-') < 2:
            category = f'{category}-未细分-未知物品'

        normalized = {
            'category': category,
            'composition': str(data.get('composition', '暂未获取到组成信息')).strip(),
            'degradation_time': str(data.get('degradation_time', '暂未获取到降解时间参考')).strip(),
            'recycling_value': str(data.get('recycling_value', '暂未获取到回收利用建议')).strip()
        }

        description_parts = []
        if normalized['composition'] and normalized['composition'] != '暂未获取到组成信息':
            description_parts.append(f"组成成分：{normalized['composition']}")
        if normalized['degradation_time'] and normalized['degradation_time'] != '暂未获取到降解时间参考':
            description_parts.append(f"降解时间：{normalized['degradation_time']}")
        if normalized['recycling_value'] and normalized['recycling_value'] != '暂未获取到回收利用建议':
            description_parts.append(f"回收建议：{normalized['recycling_value']}")

        normalized['description'] = "；".join(description_parts) if description_parts else '暂未提供详细的组成和回收信息'
        return normalized

    def _default_result(self) -> Dict[str, Any]:
        """
        当响应解析失败时提供的默认返回结构。
        """
        return {
            'category': '其他垃圾-其他类-未知物品',
            'composition': '暂未获取到组成信息',
            'degradation_time': '暂未获取到降解时间参考',
            'recycling_value': '暂未获取到回收利用建议',
            'description': '暂未提供详细的组成和回收信息'
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
                'category': '可回收物-塑料类-矿泉水瓶',
                'composition': '主要成分为聚对苯二甲酸乙二醇酯（PET）',
                'degradation_time': '在自然环境中完全降解约需400-500年',
                'recycling_value': '可循环再利用为再生塑料，建议清洗压扁后投入可回收物垃圾桶',
                'description': '组成成分：聚对苯二甲酸乙二醇酯（PET）；降解时间：约400-500年；回收建议：清洗压扁后投入可回收物垃圾桶'
            },
            {
                'category': '有害垃圾-电池类-废旧锂电池',
                'composition': '含有锂、钴、镍等金属及有机电解液',
                'degradation_time': '自然条件下难以降解，可在环境中残留数十年以上',
                'recycling_value': '含稀贵金属，需交由专业机构回收处理，避免土壤与水体污染',
                'description': '组成成分：锂、钴、镍等金属及有机电解液；降解时间：长期残留；回收建议：交由专业机构安全回收处理'
            },
            {
                'category': '厨余垃圾-果蔬类-苹果核',
                'composition': '富含纤维素、半纤维素及少量果胶和水分',
                'degradation_time': '在堆肥条件下约1-2个月即可降解',
                'recycling_value': '可进行堆肥转化为有机肥，建议沥干水分后投入厨余垃圾桶',
                'description': '组成成分：纤维素、半纤维素等；降解时间：约1-2个月；回收建议：沥干后投入厨余垃圾桶进行堆肥处理'
            },
            {
                'category': '其他垃圾-织物类-一次性口罩',
                'composition': '主要由聚丙烯无纺布、多层合成纤维',
                'degradation_time': '自然降解可能需要25年以上',
                'recycling_value': '不可回收，建议密封丢入其他垃圾桶，特殊时期应进行消毒处理',
                'description': '组成成分：聚丙烯无纺布等；降解时间：约25年以上；回收建议：不可回收，密封投入其他垃圾桶'
            }
        ]

        result = random.choice(categories)
        result['image_path'] = image_path
        result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result['detection_method'] = 'API调用'

        self.logger.info(
            "模拟识别结果: %s | 组成: %s | 降解: %s",
            result['category'],
            result['composition'],
            result['degradation_time']
        )
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
