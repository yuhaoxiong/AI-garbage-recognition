#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端 - 智能语音交流
提供与OpenAI兼容风格（如阿里DashScope兼容模式）的对话接口
"""

import logging
import time
from typing import List, Dict, Optional, Any

import requests

from utils.config_manager import get_config_manager


class LLMClient:
    """通用LLM对话客户端"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_config_manager()
        self._load_config()

    def _load_config(self):
        try:
            llm_config = self.config_manager.get_llm_config()
            self.api_url = llm_config.api_url
            self.api_key = llm_config.api_key
            self.model_name = llm_config.model_name
            self.max_retries = llm_config.max_retries
            self.timeout = llm_config.timeout
            if not self.api_url or not self.api_key:
                self.logger.warning("LLM配置不完整，聊天功能将使用本地应急回答")
        except Exception as e:
            self.logger.error(f"加载LLM配置失败: {e}")
            self.api_url = ""
            self.api_key = ""
            self.model_name = "qwen-plus"
            self.max_retries = 2
            self.timeout = 15

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.3,
             max_tokens: int = 500) -> str:
        """发送聊天请求，返回文本回复。

        Args:
            messages: [{role: "system|user|assistant", content: "..."}, ...]
        """
        # 本地兜底
        if not self.api_url or not self.api_key:
            return self._fallback_answer(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    return content.strip()
                # 兼容纯文本响应
                if isinstance(data, dict) and "output_text" in data:
                    return str(data["output_text"]).strip()
                return "抱歉，我暂时无法回答。"
            except Exception as e:
                last_error = e
                self.logger.warning(f"LLM请求失败({attempt + 1}/{self.max_retries}): {e}")
                time.sleep(0.8)

        self.logger.error(f"LLM对话失败: {last_error}")
        return self._fallback_answer(messages)

    def _fallback_answer(self, messages: List[Dict[str, str]]) -> str:
        """本地简易兜底回答：基于关键词的垃圾分类应答。"""
        try:
            # 提取最后一条用户问题
            user_text = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_text = m.get("content", "")
                    break

            user_text = user_text.strip()
            if not user_text:
                return "我在，请直接问：例如‘矿泉水瓶是什么垃圾？’"

            # 简单关键词映射
            mapping = {
                "电池": "有害垃圾",
                "药": "有害垃圾",
                "塑料瓶": "可回收物",
                "矿泉水瓶": "可回收物",
                "纸": "可回收物",
                "果皮": "湿垃圾",
                "剩饭": "湿垃圾",
            }
            for k, v in mapping.items():
                if k in user_text:
                    return f"根据常识，‘{k}’一般属于{v}。"
            return "我没太听懂，可以换个说法吗？例如：‘塑料瓶是什么垃圾？’"
        except Exception:
            return "我没太听懂，可以换个说法吗？例如：‘塑料瓶是什么垃圾？’"


_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient()
    return _llm_client_instance





