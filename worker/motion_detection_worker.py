#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运动检测工作线程 - 废弃物AI识别指导投放系统
负责检测运动、拍照和调用大模型API进行识别
"""

import cv2
import numpy as np
import time
import os
import logging
import requests
import json
import base64
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from PySide6.QtCore import QThread, Signal, QMutex, QTimer, QMutexLocker
from PySide6.QtGui import QImage, QPixmap

from utils.config_manager import get_config_manager


class MotionDetector:
    """运动检测器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.back_sub = None
        self.last_frame = None
        self.motion_threshold = config.get('motion_threshold', 500)
        self.min_contour_area = config.get('min_contour_area', 1000)
        self.detection_cooldown = config.get('detection_cooldown', 3.0)
        self.last_detection_time = 0
        
        self._initialize_background_subtractor()
    
    def _initialize_background_subtractor(self):
        """初始化背景减除器"""
        history = self.config.get('history', 500)
        dist2_threshold = self.config.get('dist2_threshold', 400.0)
        detect_shadows = self.config.get('detect_shadows', True)
        
        self.back_sub = cv2.createBackgroundSubtractorKNN(
            history=history,
            dist2Threshold=dist2_threshold,
            detectShadows=detect_shadows
        )
        logging.info("背景减除器初始化成功")
    
    def detect_motion(self, frame: np.ndarray) -> bool:
        """检测运动"""
        current_time = time.time()
        
        # 检查冷却时间
        if current_time - self.last_detection_time < self.detection_cooldown:
            return False
        
        # 应用背景减除器
        fg_mask = self.back_sub.apply(frame)
        
        # 高斯模糊减少噪声
        blur_kernel = self.config.get('blur_kernel_size', 5)
        blurred = cv2.GaussianBlur(fg_mask, (blur_kernel, blur_kernel), 0)
        
        # 二值化处理
        _, thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)
        
        # 形态学操作
        kernel_size = self.config.get('kernel_size', 3)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 检查是否有足够大的运动区域
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_contour_area:
                self.last_detection_time = current_time
                logging.info(f"检测到运动，面积: {area}")
                return True
        
        return False
    
    def reset_background(self):
        """重置背景减除器"""
        self._initialize_background_subtractor()
        logging.info("背景减除器已重置")


class APIClient:
    """大模型API客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_url = config.get('api_url', '')
        self.api_key = config.get('api_key', '')
        self.model_name = config.get('model_name', 'gpt-4-vision-preview')
        self.max_retries = config.get('max_retries', 3)
        self.timeout = config.get('timeout', 30)
        
        if not self.api_url or not self.api_key:
            logging.warning("API配置不完整，将使用模拟识别")
    
    def encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def call_api(self, image_path: str) -> Optional[Dict[str, Any]]:
        """调用大模型API识别图片"""
        if not self.api_url or not self.api_key:
            return self._mock_api_call()
        
        try:
            # 编码图片
            base64_image = self.encode_image(image_path)
            
            # 构建请求数据
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请识别这张图片中的垃圾类型，并按照以下格式返回JSON：{\"category\": \"垃圾类型\", \"confidence\": 0.95, \"description\": \"描述\"}。垃圾类型必须是：可回收物、有害垃圾、湿垃圾、干垃圾 中的一个。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300
            }
            
            # 发送请求
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=data,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # 解析JSON响应
                    try:
                        # 提取JSON部分
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start != -1 and json_end != -1:
                            json_str = content[json_start:json_end]
                            parsed_result = json.loads(json_str)
                            logging.info(f"API识别成功: {parsed_result}")
                            return parsed_result
                        else:
                            logging.warning("API响应中未找到JSON格式")
                            return self._parse_text_response(content)
                    except json.JSONDecodeError:
                        logging.warning("API响应JSON解析失败，尝试解析文本")
                        return self._parse_text_response(content)
                
                except requests.exceptions.RequestException as e:
                    logging.error(f"API请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    if attempt == self.max_retries - 1:
                        return self._mock_api_call()
                    time.sleep(1)
            
        except Exception as e:
            logging.error(f"API调用异常: {e}")
            return self._mock_api_call()
    
    def _parse_text_response(self, content: str) -> Dict[str, Any]:
        """解析文本响应"""
        content_lower = content.lower()
        
        # 简单的关键词匹配
        if "可回收" in content_lower or "recyclable" in content_lower:
            category = "可回收物"
        elif "有害" in content_lower or "hazardous" in content_lower:
            category = "有害垃圾"
        elif "湿垃圾" in content_lower or "厨余" in content_lower or "organic" in content_lower:
            category = "湿垃圾"
        elif "干垃圾" in content_lower or "其他" in content_lower or "other" in content_lower:
            category = "干垃圾"
        else:
            category = "干垃圾"  # 默认
        
        return {
            "category": category,
            "confidence": 0.7,
            "description": content
        }
    
    def _mock_api_call(self) -> Dict[str, Any]:
        """模拟API调用"""
        categories = ["可回收物", "有害垃圾", "湿垃圾", "干垃圾"]
        import random
        category = random.choice(categories)
        
        return {
            "category": category,
            "confidence": 0.8,
            "description": f"模拟识别结果：{category}"
        }


class MotionDetectionWorker(QThread):
    """运动检测工作线程"""
    
    # 信号定义
    motion_detected = Signal()  # 检测到运动
    image_captured = Signal(str)  # 图片已捕获
    api_result_received = Signal(dict)  # 收到API结果
    detection_completed = Signal(dict)  # 检测完成
    error_occurred = Signal(str)  # 发生错误
    
    def __init__(self, camera_worker=None):
        super().__init__()
        self.camera_worker = camera_worker
        self.config_manager = get_config_manager()
        
        # 加载配置
        self.motion_config = self.config_manager.get_motion_detection_config()
        self.api_config = self.config_manager.get_api_config()
        
        # 初始化组件
        self.motion_detector = MotionDetector(self.motion_config)
        self.api_client = APIClient(self.api_config)
        
        # 状态控制
        self.is_running = False
        self.is_enabled = False
        self.mutex = QMutex()
        
        # 图片保存目录
        self.image_dir = "data/captured_images"
        os.makedirs(self.image_dir, exist_ok=True)
        
        logging.info("运动检测工作线程初始化完成")
    
    def enable_detection(self, enabled: bool):
        """启用/禁用检测"""
        locker = QMutexLocker(self.mutex)
        self.is_enabled = enabled
        logging.info(f"运动检测已{'启用' if enabled else '禁用'}")
        # locker 离开作用域自动释放锁
    
    def reset_background(self):
        """重置背景减除器"""
        self.motion_detector.reset_background()
    
    def run(self):
        """运行检测循环"""
        self.is_running = True
        logging.info("运动检测工作线程开始运行")
        
        try:
            while self.is_running:
                if not self.is_enabled:
                    time.sleep(0.1)
                    continue
                
                # 获取当前帧
                if self.camera_worker and hasattr(self.camera_worker, 'get_current_frame'):
                    frame = self.camera_worker.get_current_frame()
                    if frame is not None:
                        # 检测运动
                        if self.motion_detector.detect_motion(frame):
                            self.motion_detected.emit()
                            
                            # 捕获图片
                            image_path = self._capture_image(frame)
                            if image_path:
                                self.image_captured.emit(image_path)
                                
                                # 调用API识别
                                self._call_api_for_recognition(image_path)
                
                time.sleep(0.1)  # 控制检测频率
        
        except Exception as e:
            logging.error(f"运动检测工作线程异常: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.is_running = False
            logging.info("运动检测工作线程已停止")
    
    def _capture_image(self, frame: np.ndarray) -> Optional[str]:
        """捕获图片"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"motion_detected_{timestamp}.jpg"
            image_path = os.path.join(self.image_dir, filename)
            
            # 保存图片
            cv2.imwrite(image_path, frame)
            logging.info(f"图片已保存: {image_path}")
            
            return image_path
        
        except Exception as e:
            logging.error(f"图片保存失败: {e}")
            self.error_occurred.emit(f"图片保存失败: {e}")
            return None
    
    def _call_api_for_recognition(self, image_path: str):
        """调用API进行识别"""
        try:
            logging.info("开始调用API进行识别...")
            
            # 调用API
            result = self.api_client.call_api(image_path)
            
            if result:
                self.api_result_received.emit(result)
                
                # 构建检测结果
                detection_result = {
                    "category": result.get("category", "未知"),
                    "confidence": result.get("confidence", 0.0),
                    "description": result.get("description", ""),
                    "image_path": image_path,
                    "detection_method": "motion_detection",
                    "timestamp": datetime.now().isoformat()
                }
                
                self.detection_completed.emit(detection_result)
                logging.info(f"运动检测识别完成: {detection_result}")
            else:
                self.error_occurred.emit("API识别失败")
        
        except Exception as e:
            logging.error(f"API识别异常: {e}")
            self.error_occurred.emit(f"API识别异常: {e}")
    
    def stop(self):
        """停止工作线程"""
        self.is_running = False
        self.wait()
        logging.info("运动检测工作线程已停止") 