#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音调试工具 - 废弃物AI识别指导投放系统
用于调试和监控语音播放情况，帮助发现重复播放问题
"""

import logging
import time
import threading
from typing import Dict, List, Any
from collections import defaultdict, deque
from datetime import datetime


class VoiceDebugMonitor:
    """语音调试监控器"""
    
    def __init__(self, max_history=100):
        self.logger = logging.getLogger(__name__)
        self.max_history = max_history
        
        # 语音播放历史
        self.play_history = deque(maxlen=max_history)
        
        # 统计信息
        self.statistics = {
            'total_calls': 0,
            'duplicate_calls': 0,
            'concurrent_calls': 0,
            'last_reset_time': time.time()
        }
        
        # 当前播放状态
        self.current_playing = {}
        self.lock = threading.Lock()
        
        # 重复检测参数
        self.duplicate_threshold = 1.0  # 1秒内的重复调用被认为是重复
        
    def log_voice_call(self, text: str, source: str = "unknown", priority: str = "normal"):
        """记录语音调用
        
        Args:
            text: 语音文本
            source: 调用源（如MainWindow, GuidanceWidget等）
            priority: 优先级
        """
        with self.lock:
            timestamp = time.time()
            call_info = {
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3],
                'text': text,
                'source': source,
                'priority': priority,
                'thread_id': threading.get_ident()
            }
            
            # 添加到历史记录
            self.play_history.append(call_info)
            self.statistics['total_calls'] += 1
            
            # 检查是否为重复调用
            if self._is_duplicate_call(call_info):
                self.statistics['duplicate_calls'] += 1
                self.logger.warning(f"🔄 检测到重复语音调用: {text[:30]}... (来源: {source})")
                
            # 检查并发调用
            if self._is_concurrent_call(call_info):
                self.statistics['concurrent_calls'] += 1
                self.logger.warning(f"⚠️ 检测到并发语音调用: {text[:30]}... (来源: {source})")
            
            # 记录当前播放状态
            self.current_playing[text] = call_info
            
            self.logger.debug(f"🎵 语音调用记录: [{source}] {text[:50]}...")
    
    def log_voice_completed(self, text: str):
        """记录语音播放完成"""
        with self.lock:
            if text in self.current_playing:
                call_info = self.current_playing.pop(text)
                duration = time.time() - call_info['timestamp']
                self.logger.debug(f"✅ 语音播放完成: {text[:30]}... (耗时: {duration:.2f}s)")
    
    def _is_duplicate_call(self, call_info: Dict[str, Any]) -> bool:
        """检查是否为重复调用"""
        if len(self.play_history) < 2:
            return False
        
        # 检查最近的调用
        recent_calls = [call for call in self.play_history 
                       if call_info['timestamp'] - call['timestamp'] <= self.duplicate_threshold
                       and call != call_info]
        
        # 检查是否有相同或相似的文本
        for recent_call in recent_calls:
            if (recent_call['text'] == call_info['text'] or 
                self._is_similar_text(recent_call['text'], call_info['text'])):
                return True
        
        return False
    
    def _is_concurrent_call(self, call_info: Dict[str, Any]) -> bool:
        """检查是否为并发调用"""
        # 如果当前有其他语音正在播放，则认为是并发调用
        return len(self.current_playing) > 0
    
    def _is_similar_text(self, text1: str, text2: str) -> bool:
        """检查两个文本是否相似"""
        # 简单的相似度检查
        if len(text1) == 0 or len(text2) == 0:
            return False
        
        # 如果一个文本包含另一个，认为是相似的
        if text1 in text2 or text2 in text1:
            return True
        
        # 检查关键词重叠
        words1 = set(text1.split())
        words2 = set(text2.split())
        overlap = len(words1.intersection(words2))
        
        # 如果重叠词汇超过50%，认为是相似的
        min_words = min(len(words1), len(words2))
        if min_words > 0 and overlap / min_words > 0.5:
            return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            runtime = time.time() - self.statistics['last_reset_time']
            stats = self.statistics.copy()
            stats['runtime_seconds'] = runtime
            stats['calls_per_minute'] = stats['total_calls'] / (runtime / 60) if runtime > 0 else 0
            stats['duplicate_rate'] = stats['duplicate_calls'] / stats['total_calls'] if stats['total_calls'] > 0 else 0
            stats['concurrent_rate'] = stats['concurrent_calls'] / stats['total_calls'] if stats['total_calls'] > 0 else 0
            stats['currently_playing'] = len(self.current_playing)
            return stats
    
    def get_recent_calls(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的语音调用记录"""
        with self.lock:
            return list(self.play_history)[-count:]
    
    def get_duplicate_calls(self) -> List[Dict[str, Any]]:
        """获取重复调用记录"""
        with self.lock:
            duplicates = []
            seen_texts = defaultdict(list)
            
            # 按文本分组
            for call in self.play_history:
                seen_texts[call['text']].append(call)
            
            # 找出重复的调用
            for text, calls in seen_texts.items():
                if len(calls) > 1:
                    # 检查时间间隔
                    for i in range(1, len(calls)):
                        time_diff = calls[i]['timestamp'] - calls[i-1]['timestamp']
                        if time_diff <= self.duplicate_threshold:
                            duplicates.append({
                                'text': text,
                                'calls': [calls[i-1], calls[i]],
                                'time_diff': time_diff
                            })
            
            return duplicates
    
    def print_report(self):
        """打印调试报告"""
        stats = self.get_statistics()
        recent_calls = self.get_recent_calls(5)
        duplicates = self.get_duplicate_calls()
        
        print("\n" + "="*60)
        print("🎵 语音调试报告")
        print("="*60)
        
        print(f"\n📊 统计信息:")
        print(f"  总调用次数: {stats['total_calls']}")
        print(f"  重复调用次数: {stats['duplicate_calls']}")
        print(f"  并发调用次数: {stats['concurrent_calls']}")
        print(f"  当前播放数量: {stats['currently_playing']}")
        print(f"  运行时间: {stats['runtime_seconds']:.1f}秒")
        print(f"  调用频率: {stats['calls_per_minute']:.1f}次/分钟")
        print(f"  重复率: {stats['duplicate_rate']:.1%}")
        print(f"  并发率: {stats['concurrent_rate']:.1%}")
        
        if recent_calls:
            print(f"\n📝 最近调用记录:")
            for call in recent_calls:
                print(f"  [{call['datetime']}] {call['source']}: {call['text'][:40]}...")
        
        if duplicates:
            print(f"\n⚠️ 重复调用检测:")
            for dup in duplicates[:5]:  # 只显示前5个
                time_diff = dup['time_diff']
                print(f"  文本: {dup['text'][:40]}...")
                print(f"  时间间隔: {time_diff:.3f}秒")
                for call in dup['calls']:
                    print(f"    [{call['datetime']}] {call['source']}")
                print()
        
        print("="*60)
    
    def reset_statistics(self):
        """重置统计信息"""
        with self.lock:
            self.statistics = {
                'total_calls': 0,
                'duplicate_calls': 0,
                'concurrent_calls': 0,
                'last_reset_time': time.time()
            }
            self.play_history.clear()
            self.current_playing.clear()
            self.logger.info("语音调试统计信息已重置")


# 全局调试监控器实例
_debug_monitor = None

def get_voice_debug_monitor() -> VoiceDebugMonitor:
    """获取语音调试监控器实例"""
    global _debug_monitor
    if _debug_monitor is None:
        _debug_monitor = VoiceDebugMonitor()
    return _debug_monitor


def enable_voice_debug():
    """启用语音调试模式"""
    # 设置日志级别
    logging.getLogger('utils.voice_debug').setLevel(logging.DEBUG)
    
    # 获取监控器实例
    monitor = get_voice_debug_monitor()
    
    print("🔧 语音调试模式已启用")
    print("使用以下方法监控语音:")
    print("  from utils.voice_debug import get_voice_debug_monitor")
    print("  monitor = get_voice_debug_monitor()")
    print("  monitor.print_report()")
    
    return monitor


def disable_voice_debug():
    """禁用语音调试模式"""
    global _debug_monitor
    if _debug_monitor:
        _debug_monitor.reset_statistics()
        _debug_monitor = None
    
    # 恢复日志级别
    logging.getLogger('utils.voice_debug').setLevel(logging.WARNING)
    
    print("🔧 语音调试模式已禁用")


if __name__ == "__main__":
    # 测试代码
    monitor = enable_voice_debug()
    
    # 模拟一些语音调用
    monitor.log_voice_call("欢迎使用智能垃圾分类系统", "MainWindow", "normal")
    time.sleep(0.5)
    monitor.log_voice_call("欢迎使用智能垃圾分类系统", "GuidanceWidget", "normal")  # 重复调用
    time.sleep(0.1)
    monitor.log_voice_call("检测到可回收物", "MotionDetection", "high")
    
    # 打印报告
    monitor.print_report()
