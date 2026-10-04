"""
腾讯混元生图模块 - 文生图API调用
"""
import base64
import time
import os
from typing import Optional
from datetime import datetime

# 获取脚本所在目录，确保路径正确
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class HunyuanImageGenerator:
    """混元文生图生成器"""

    def __init__(self, secret_id: str, secret_key: str, region: str = "ap-guangzhou"):
        """
        初始化图片生成器

        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 地域，默认广州
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region

        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.aiart.v20221229 import aiart_client, models as aiart_models
            from tencentcloud.hunyuan.v20230901 import hunyuan_client, models as hunyuan_models

            self.credential = credential.Credential(secret_id, secret_key)
            self.http_profile = HttpProfile(endpoint="aiart.tencentcloudapi.com")
            self.client_profile = ClientProfile(httpProfile=self.http_profile)

            self.aiart_client = aiart_client.AiartClient(self.credential, region, self.client_profile)

            hunyuan_http_profile = HttpProfile(endpoint="hunyuan.tencentcloudapi.com")
            hunyuan_client_profile = ClientProfile(httpProfile=hunyuan_http_profile)
            self.hunyuan_client = hunyuan_client.HunyuanClient(self.credential, region, hunyuan_client_profile)

            self.aiart_models = aiart_models
            self.hunyuan_models = hunyuan_models

        except ImportError:
            raise ImportError(
                "请安装腾讯云SDK: pip install tencentcloud-sdk-python\n"
                "或: pip install tencentcloud-sdk-python-aiart tencentcloud-sdk-python-hunyuan"
            )

    def generate_image_lite(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        resolution: str = "1024:1024",
        return_url: bool = True,
        logo_add: int = 0
    ) -> dict:
        """
        极速版文生图 - 同步返回结果

        Args:
            prompt: 文本描述
            negative_prompt: 反向提示词
            resolution: 分辨率，如 "1024:1024", "768:1024", "1024:768"
            return_url: 是否返回URL，False则返回base64
            logo_add: 是否添加水印，0不添加，1添加

        Returns:
            包含图片URL或base64的字典
        """
        req = self.aiart_models.TextToImageLiteRequest()
        req.Prompt = prompt
        req.Resolution = resolution
        req.LogoAdd = logo_add
        req.RspImgType = "url" if return_url else "base64"

        if negative_prompt:
            req.NegativePrompt = negative_prompt

        response = self.aiart_client.TextToImageLite(req)

        result = {
            "success": True,
            "seed": response.Seed,
            "request_id": response.RequestId
        }

        if return_url:
            result["image_url"] = response.ResultImage
        else:
            result["image_base64"] = response.ResultImage

        return result

    def submit_image_job(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = None,
        resolution: str = "1024:1024",
        revise: bool = True
    ) -> dict:
        """
        提交混元生图任务 - 异步模式

        Args:
            prompt: 文本描述
            negative_prompt: 反向提示词
            style: 绘画风格
            resolution: 分辨率
            revise: 是否开启prompt扩写

        Returns:
            包含任务ID的字典
        """
        req = self.hunyuan_models.SubmitHunyuanImageJobRequest()
        req.Prompt = prompt
        req.Revise = revise

        if negative_prompt:
            req.NegativePrompt = negative_prompt
        if style:
            req.Style = style

        response = self.hunyuan_client.SubmitHunyuanImageJob(req)

        return {
            "success": True,
            "job_id": response.JobId,
            "request_id": response.RequestId
        }

    def query_image_job(self, job_id: str) -> dict:
        """
        查询生图任务状态

        Args:
            job_id: 任务ID

        Returns:
            任务状态和结果
        """
        req = self.hunyuan_models.QueryHunyuanImageJobRequest()
        req.JobId = job_id

        response = self.hunyuan_client.QueryHunyuanImageJob(req)

        status_map = {
            "1": "排队中",
            "2": "处理中",
            "4": "处理失败",
            "5": "处理完成"
        }

        result = {
            "success": True,
            "job_id": job_id,
            "status_code": response.JobStatusCode,
            "status_msg": response.JobStatusMsg,
            "status_text": status_map.get(response.JobStatusCode, "未知状态"),
            "request_id": response.RequestId
        }

        if response.JobStatusCode == "5":
            result["image_urls"] = response.ResultImage
            result["revised_prompt"] = response.RevisedPrompt
        elif response.JobStatusCode == "4":
            result["error_code"] = response.JobErrorCode
            result["error_msg"] = response.JobErrorMsg

        return result

    def generate_image_async(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = None,
        timeout: int = 300,
        poll_interval: int = 3
    ) -> dict:
        """
        异步生图（自动轮询等待结果）

        Args:
            prompt: 文本描述
            negative_prompt: 反向提示词
            style: 绘画风格
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            生成结果
        """
        submit_result = self.submit_image_job(prompt, negative_prompt, style)
        if not submit_result["success"]:
            return submit_result

        job_id = submit_result["job_id"]
        print(f"任务已提交，Job ID: {job_id}")
        print("正在生成图片...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.query_image_job(job_id)

            if result["status_code"] == "5":
                return result
            elif result["status_code"] == "4":
                return result

            print(f"状态: {result['status_text']}")
            time.sleep(poll_interval)

        return {
            "success": False,
            "error": "生成超时",
            "job_id": job_id
        }

    def save_image(self, image_url: str, save_path: str) -> str:
        """
        保存图片到本地

        Args:
            image_url: 图片URL
            save_path: 保存路径

        Returns:
            保存的文件路径
        """
        import requests

        response = requests.get(image_url)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)

        return save_path


def generate_image(
    prompt: str,
    secret_id: str,
    secret_key: str,
    negative_prompt: Optional[str] = None,
    resolution: str = "1024:1024",
    save_dir: str = None
) -> dict:
    """
    便捷函数：生成图片并保存

    Args:
        prompt: 文本描述
        secret_id: 腾讯云 SecretId
        secret_key: 腾讯云 SecretKey
        negative_prompt: 反向提示词
        resolution: 分辨率
        save_dir: 保存目录，默认为 BASE_DIR/generated_images

    Returns:
        生成结果
    """
    if save_dir is None:
        save_dir = os.path.join(BASE_DIR, "generated_images")
    generator = HunyuanImageGenerator(secret_id, secret_key)

    result = generator.generate_image_lite(
        prompt=prompt,
        negative_prompt=negative_prompt,
        resolution=resolution
    )

    if result.get("image_url"):
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hunyuan_{timestamp}.png"
        save_path = os.path.join(save_dir, filename)

        generator.save_image(result["image_url"], save_path)
        result["local_path"] = save_path
        print(f"图片已保存: {save_path}")

    return result


if __name__ == "__main__":
    import os

    secret_id = os.getenv("TENCENT_SECRET_ID")
    secret_key = os.getenv("TENCENT_SECRET_KEY")

    if not secret_id or not secret_key:
        print("请设置环境变量:")
        print("  export TENCENT_SECRET_ID=你的SecretId")
        print("  export TENCENT_SECRET_KEY=你的SecretKey")
    else:
        result = generate_image(
            prompt="一只可爱的猫咪在花园里玩耍，阳光明媚",
            secret_id=secret_id,
            secret_key=secret_key
        )
        print(f"生成结果: {result}")