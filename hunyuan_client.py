"""
腾讯云混元大模型客户端 - 核心API调用模块
"""
import os
from typing import List, Dict, Optional, Union, Iterator
from openai import OpenAI
from hunyuan_config import HunyuanConfig


class HunyuanClient:
    """腾讯云混元大模型客户端"""

    def __init__(self, config: Optional[HunyuanConfig] = None):
        """
        初始化混元大模型客户端

        Args:
            config: 混元配置对象，如果为None则从环境变量加载
        """
        if config is None:
            config = HunyuanConfig.from_env()

        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=3
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, Iterator]:
        """
        发送对话请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大token数
            stream: 是否使用流式输出
            **kwargs: 其他参数

        Returns:
            非流式返回完整响应字典，流式返回迭代器
        """
        request_params = {
            "model": model or self.config.model,
            "messages": messages,
            "stream": stream
        }

        if temperature is not None:
            request_params["temperature"] = temperature
        elif self.config.temperature:
            request_params["temperature"] = self.config.temperature

        if max_tokens is not None:
            request_params["max_tokens"] = max_tokens
        elif self.config.max_tokens:
            request_params["max_tokens"] = self.config.max_tokens

        request_params.update(kwargs)

        response = self.client.chat.completions.create(**request_params)

        if stream:
            return response
        else:
            return response.model_dump()

    def simple_chat(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        """
        简单对话接口

        Args:
            user_input: 用户输入
            system_prompt: 系统提示词

        Returns:
            模型生成的回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})

        response = self.chat(messages)
        return response["choices"][0]["message"]["content"]

    def stream_chat(
        self,
        messages: List[Dict[str, str]]
    ) -> Iterator[str]:
        """
        流式对话

        Args:
            messages: 消息列表

        Yields:
            生成的文本片段
        """
        stream_response = self.chat(messages, stream=True)
        for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def multi_turn_chat(
        self,
        messages: List[Dict[str, str]],
        user_input: str
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        多轮对话

        Args:
            messages: 历史消息列表
            user_input: 用户新输入

        Returns:
            (模型回复, 更新后的消息列表)
        """
        messages.append({"role": "user", "content": user_input})
        response = self.chat(messages)
        assistant_message = response["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message, messages