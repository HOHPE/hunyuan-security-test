"""
对话会话管理模块 - 管理多轮对话和会话历史
"""
from typing import List, Dict, Optional
from datetime import datetime
from hunyuan_client import HunyuanClient


class ConversationManager:
    """对话会话管理器"""

    def __init__(self, client: HunyuanClient, system_prompt: Optional[str] = None):
        """
        初始化会话管理器

        Args:
            client: HunyuanClient实例
            system_prompt: 系统提示词
        """
        self.client = client
        self.system_prompt = system_prompt or "你是一个有用的AI助手。"
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
        self.session_metadata: Dict[str, dict] = {}

    def create_session(self, session_id: str) -> None:
        """创建新会话"""
        self.conversations[session_id] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.session_metadata[session_id] = {
            "created_at": datetime.now(),
            "message_count": 0
        }

    def get_or_create_session(self, session_id: str) -> List[Dict[str, str]]:
        """获取或创建会话"""
        if session_id not in self.conversations:
            self.create_session(session_id)
        return self.conversations[session_id]

    def send_message(
        self,
        session_id: str,
        user_input: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        发送消息并获取回复

        Args:
            session_id: 会话ID
            user_input: 用户输入
            temperature: 温度参数

        Returns:
            模型回复
        """
        messages = self.get_or_create_session(session_id)
        messages.append({"role": "user", "content": user_input})

        response = self.client.chat(messages, temperature=temperature)
        assistant_message = response["choices"][0]["message"]["content"]

        messages.append({"role": "assistant", "content": assistant_message})
        self.session_metadata[session_id]["message_count"] += 1

        return assistant_message

    def stream_send_message(
        self,
        session_id: str,
        user_input: str
    ):
        """
        流式发送消息

        Args:
            session_id: 会话ID
            user_input: 用户输入

        Yields:
            生成的文本片段
        """
        messages = self.get_or_create_session(session_id)
        messages.append({"role": "user", "content": user_input})

        full_response = ""
        for chunk in self.client.stream_chat(messages):
            full_response += chunk
            yield chunk

        messages.append({"role": "assistant", "content": full_response})
        self.session_metadata[session_id]["message_count"] += 1

    def clear_session(self, session_id: str) -> None:
        """清除会话历史"""
        if session_id in self.conversations:
            self.conversations[session_id] = [
                {"role": "system", "content": self.system_prompt}
            ]

    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        if session_id in self.conversations:
            del self.conversations[session_id]
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取会话信息"""
        if session_id in self.session_metadata:
            info = self.session_metadata[session_id].copy()
            info["message_count"] = len(self.conversations.get(session_id, [])) - 1
            return info
        return None