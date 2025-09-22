#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
废弃物AI检测工作器 - 废弃物AI识别指导投放系统
负责摄像头图像采集、AI检测和分类识别
"""

import cv2
import numpy as np
import time
import logging
import threading
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

try:
    from rknnlite.api import RKNNLite
    RKNN_AVAILABLE = True
except ImportError:
    RKNN_AVAILABLE = False
    print("警告: RKNN库未安装，将使用模拟检测")

from utils.config_manager import get_config_manager


@dataclass
class WasteDetectionResult:
    """废弃物检测结果"""
    class_name: str          # AI识别的类别名
    waste_category: str      # 垃圾分类
    confidence: float        # 置信度
    bbox: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)
    guidance: str           # 投放指导
    color: str             # 分类颜色


class WasteDetector:
    """废弃物检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self.config_manager = get_config_manager()
        self.ai_config = self.config_manager.get_ai_detection_config()
        self.waste_categories = self.config_manager.get_waste_categories()
        self.ai_model_config = self.config_manager.get_ai_model_config()
        self.logger = logging.getLogger(__name__)
        
        # AI模型配置
        self.model_path = self.ai_config.model_path
        self.confidence_threshold = self.ai_config.confidence_threshold
        self.nms_threshold = self.ai_config.nms_threshold
        self.input_size = self.ai_config.input_size
        
        # 类别映射
        self.class_mapping = self.ai_model_config.get('class_mapping', {})
        self.classes = self.ai_model_config.get('classes', [])
        
        # 初始化模型
        self.rknn = None
        self._init_model()
    
    def _init_model(self):
        """初始化AI模型"""
        try:
            if RKNN_AVAILABLE and self.model_path:
                self.rknn = RKNNLite()
                
                # 加载模型
                ret = self.rknn.load_rknn(self.model_path)
                if ret != 0:
                    self.logger.error("加载RKNN模型失败")
                    self.rknn = None
                    return
                
                # 初始化运行时环境
                ret = self.rknn.init_runtime()
                if ret != 0:
                    self.logger.error("初始化RKNN运行时失败")
                    self.rknn = None
                    return
                
                self.logger.info("RKNN模型初始化成功")
            else:
                self.logger.warning("RKNN不可用，将使用模拟检测")
                
        except Exception as e:
            self.logger.error(f"模型初始化失败: {e}")
            self.rknn = None
    
    def detect(self, image: np.ndarray) -> List[WasteDetectionResult]:
        """
        检测图像中的废弃物
        
        Args:
            image: 输入图像
            
        Returns:
            检测结果列表
        """
        if self.rknn is None:
            return self._mock_detect(image)
        
        try:
            # 预处理图像
            processed_image = self._preprocess_image(image)
            
            # AI推理
            outputs = self.rknn.inference(inputs=[processed_image])
            
            # 后处理
            results = self._postprocess(outputs, image.shape[:2])
            
            return results
            
        except Exception as e:
            self.logger.error(f"检测失败: {e}")
            return []
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像
        
        Args:
            image: 原始图像
            
        Returns:
            预处理后的图像
        """
        # 调整尺寸
        resized = cv2.resize(image, (self.input_size, self.input_size))
        
        # 归一化
        normalized = resized.astype(np.float32) / 255.0
        
        # 转换为模型输入格式 (1, 3, H, W)
        input_data = np.transpose(normalized, (2, 0, 1))
        input_data = np.expand_dims(input_data, axis=0)
        
        return input_data
    
    def _postprocess(self, outputs: List[np.ndarray], original_shape: Tuple[int, int]) -> List[WasteDetectionResult]:
        """
        后处理检测结果
        
        Args:
            outputs: AI模型输出
            original_shape: 原始图像尺寸 (height, width)
            
        Returns:
            检测结果列表
        """
        results = []
        
        try:
            # 解析YOLO输出（简化版本）
            for output in outputs:
                # 假设输出格式为 (batch, boxes, 5 + num_classes)
                # 其中 5 = x, y, w, h, confidence
                if len(output.shape) == 3:
                    output = output[0]  # 移除batch维度
                
                # 筛选置信度高的检测框
                for detection in output:
                    if len(detection) < 5:
                        continue
                    
                    # 解析检测数据
                    x, y, w, h, confidence = detection[:5]
                    
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # 获取类别概率
                    class_probs = detection[5:] if len(detection) > 5 else []
                    if len(class_probs) == 0:
                        continue
                    
                    # 找到最高概率的类别
                    class_id = np.argmax(class_probs)
                    class_confidence = class_probs[class_id] * confidence
                    
                    if class_confidence < self.confidence_threshold:
                        continue
                    
                    # 转换坐标
                    scale_x = original_shape[1] / self.input_size
                    scale_y = original_shape[0] / self.input_size
                    
                    x1 = int((x - w/2) * scale_x)
                    y1 = int((y - h/2) * scale_y)
                    x2 = int((x + w/2) * scale_x)
                    y2 = int((y + h/2) * scale_y)
                    
                    # 获取类别名称
                    class_name = self.classes[class_id] if class_id < len(self.classes) else f"class_{class_id}"
                    
                    # 映射到垃圾分类
                    waste_category = self.class_mapping.get(class_name, "未知分类")
                    
                    # 获取分类信息
                    category_info = self.config_manager.get_waste_category_info(waste_category)
                    if category_info:
                        guidance = category_info.get('guidance', '请咨询工作人员')
                        color = category_info.get('color', '#808080')
                    else:
                        guidance = '请咨询工作人员'
                        color = '#808080'
                    
                    # 创建检测结果
                    result = WasteDetectionResult(
                        class_name=class_name,
                        waste_category=waste_category,
                        confidence=float(class_confidence),
                        bbox=(x1, y1, x2, y2),
                        guidance=guidance,
                        color=color
                    )
                    
                    results.append(result)
            
            # NMS去重
            results = self._apply_nms(results)
            
        except Exception as e:
            self.logger.error(f"后处理失败: {e}")
        
        return results
    
    def _apply_nms(self, results: List[WasteDetectionResult]) -> List[WasteDetectionResult]:
        """
        应用非极大值抑制
        
        Args:
            results: 检测结果列表
            
        Returns:
            去重后的结果列表
        """
        if len(results) <= 1:
            return results
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 简单的NMS实现
        filtered_results = []
        for i, result in enumerate(results):
            keep = True
            for j in range(i):
                if self._calculate_iou(result.bbox, results[j].bbox) > self.nms_threshold:
                    keep = False
                    break
            
            if keep:
                filtered_results.append(result)
        
        return filtered_results
    
    def _calculate_iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """
        计算两个边界框的IoU
        
        Args:
            box1: 边界框1 (x1, y1, x2, y2)
            box2: 边界框2 (x1, y1, x2, y2)
            
        Returns:
            IoU值
        """
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 计算交集
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)
        
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # 计算并集
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = area1 + area2 - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def _mock_detect(self, image: np.ndarray) -> List[WasteDetectionResult]:
        """
        模拟检测（用于测试）
        
        Args:
            image: 输入图像
            
        Returns:
            模拟检测结果
        """
        # 生成随机检测结果用于测试
        mock_results = [
            WasteDetectionResult(
                class_name="plastic_bottle",
                waste_category="可回收物",
                confidence=0.85,
                bbox=(100, 100, 200, 300),
                guidance="请清洗干净后投放到蓝色可回收物垃圾桶",
                color="#0080ff"
            )
        ]
        
        return mock_results
    
    def __del__(self):
        """析构函数"""
        if self.rknn is not None:
            self.rknn.release()


class WasteDetectionWorker(QThread):
    """废弃物检测工作线程"""
    
    # 信号定义
    frame_processed = Signal(np.ndarray)  # 处理后的帧
    detection_result = Signal(list)       # 检测结果
    fps_updated = Signal(float)           # FPS更新
    error_occurred = Signal(str)          # 错误信号
    status_changed = Signal(str)          # 状态变化
    
    def __init__(self):
        """初始化工作线程"""
        super().__init__()
        
        self.config_manager = get_config_manager()
        self.camera_config = self.config_manager.get_camera_config()
        self.logger = logging.getLogger(__name__)
        
        # 摄像头配置
        self.device_id = self.camera_config.device_id
        self.resolution = self.camera_config.resolution
        self.fps_target = self.camera_config.fps
        
        # 控制变量
        self.running = False
        self.paused = False
        self.io_detection_enabled = False  # IO控制检测开关
        self.mutex = QMutex()
        
        # 摄像头和检测器
        self.cap = None
        self.detector = WasteDetector()
        
        # FPS计算
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0.0
        
    def start_detection(self):
        """开始检测"""
        with QMutexLocker(self.mutex):
            if not self.running:
                self.running = True
                self.paused = False
                self.start()
                self.status_changed.emit("启动中...")
    
    def stop_detection(self):
        """停止检测"""
        with QMutexLocker(self.mutex):
            self.running = False
            self.paused = False
        
        self.wait()  # 等待线程结束
        self.status_changed.emit("已停止")
    
    def pause_detection(self):
        """暂停检测"""
        with QMutexLocker(self.mutex):
            self.paused = True
        self.status_changed.emit("已暂停")
    
    def resume_detection(self):
        """恢复检测"""
        with QMutexLocker(self.mutex):
            self.paused = False
        self.status_changed.emit("运行中")
    
    def get_io_detection_status(self) -> bool:
        """获取IO检测状态"""
        with QMutexLocker(self.mutex):
            return self.io_detection_enabled
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """获取当前帧"""
        return self.current_frame if hasattr(self, 'current_frame') else None
    
    def enable_io_detection(self, enabled: bool):
        """启用/禁用IO控制检测"""
        with QMutexLocker(self.mutex):
            self.io_detection_enabled = enabled
            
        if enabled:
            self.status_changed.emit("IO检测已启用")
            self.logger.info("IO控制检测已启用")
        else:
            self.status_changed.emit("IO检测已禁用")
            self.logger.info("IO控制检测已禁用")
    
    def run(self):
        """线程主循环"""
        try:
            self._init_camera()
            
            if self.cap is None or not self.cap.isOpened():
                self.error_occurred.emit("无法打开摄像头")
                return
            
            self.status_changed.emit("运行中")
            
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # 读取帧
                ret, frame = self.cap.read()
                if not ret:
                    self.error_occurred.emit("读取摄像头帧失败")
                    break
                
                # 检测废弃物（仅在IO控制开启时进行）
                detection_results = []
                if self.io_detection_enabled:
                    detection_results = self.detector.detect(frame)
                
                # 绘制检测结果
                annotated_frame = self._draw_results(frame, detection_results)
                
                # 发送信号
                self.frame_processed.emit(annotated_frame)
                
                # 只在有检测结果时发送检测信号
                if detection_results or self.io_detection_enabled:
                    self.detection_result.emit(detection_results)
                
                # 更新FPS
                self._update_fps()
                
                # 控制帧率
                time.sleep(1.0 / self.fps_target)
                
        except Exception as e:
            self.logger.error(f"检测线程异常: {e}")
            self.error_occurred.emit(f"检测异常: {str(e)}")
        
        finally:
            self._cleanup()
    
    def _init_camera(self):
        """初始化摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if self.cap.isOpened():
                # 设置分辨率
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution['width'])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution['height'])
                
                # 设置FPS
                self.cap.set(cv2.CAP_PROP_FPS, self.fps_target)
                
                self.logger.info(f"摄像头初始化成功: 设备ID={self.device_id}")
            else:
                self.logger.error("摄像头打开失败")
                self.cap = None
                
        except Exception as e:
            self.logger.error(f"摄像头初始化失败: {e}")
            self.cap = None
    
    def _draw_results(self, frame: np.ndarray, results: List[WasteDetectionResult]) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            frame: 原始图像
            results: 检测结果列表
            
        Returns:
            绘制后的图像
        """
        annotated_frame = frame.copy()
        
        for result in results:
            x1, y1, x2, y2 = result.bbox
            
            # 转换颜色
            color_hex = result.color.lstrip('#')
            color_bgr = tuple(int(color_hex[i:i+2], 16) for i in (4, 2, 0))  # BGR格式
            
            # 绘制边界框
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color_bgr, 2)
            
            # 绘制标签
            label = f"{result.waste_category} ({result.confidence:.2f})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            
            # 绘制标签背景
            cv2.rectangle(annotated_frame, 
                         (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), 
                         color_bgr, -1)
            
            # 绘制标签文本
            cv2.putText(annotated_frame, label, 
                       (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return annotated_frame
    
    def _update_fps(self):
        """更新FPS计算"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_timer)
            self.fps_updated.emit(self.current_fps)
            
            self.fps_counter = 0
            self.fps_timer = current_time
    
    def _cleanup(self):
        """清理资源"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None 

    def stop(self):
        """安全停止线程"""
        self.stop_detection()
        self._cleanup()
        self.quit()
        self.wait() 