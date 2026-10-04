"""
配置模块 - 管理腾讯云混元大模型API配置
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HunyuanConfig:
    """混元大模型配置类"""
    api_key: str
    base_url: str = "https://api.hunyuan.cloud.tencent.com/v1"
    model: str = "hunyuan-turbos-latest"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None

    @classmethod
    def from_env(cls):
        """从环境变量创建配置"""
        api_key = os.getenv("HUNYUAN_API_KEY")
        if not api_key:
            raise ValueError("未设置HUNYUAN_API_KEY环境变量")

        secret_id = os.getenv("TENCENT_SECRET_ID")
        secret_key = os.getenv("TENCENT_SECRET_KEY")

        return cls(
            api_key=api_key,
            secret_id=secret_id,
            secret_key=secret_key
        )

    @classmethod
    def from_file(cls, config_path: str = "config.json"):
        """从配置文件创建配置"""
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return cls(**config_data)