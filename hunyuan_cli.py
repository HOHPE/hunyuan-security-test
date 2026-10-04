"""
命令行交互式工具 - 提供交互式的混元大模型对话体验
"""
import os
import sys
from datetime import datetime
from hunyuan_config import HunyuanConfig
from hunyuan_client import HunyuanClient
from hunyuan_conversation import ConversationManager

# 获取脚本所在目录，确保路径正确
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class HunyuanCLI:
    """混元大模型命令行工具"""

    def __init__(self):
        """初始化CLI"""
        self.config = None

        try:
            self.config = HunyuanConfig.from_env()
        except ValueError:
            try:
                config_path = os.path.join(BASE_DIR, "config.json")
                self.config = HunyuanConfig.from_file(config_path)
            except FileNotFoundError:
                print("错误: 未找到配置")
                print("请设置 HUNYUAN_API_KEY 环境变量，或创建 config.json 配置文件")
                sys.exit(1)
            except Exception as e:
                print(f"错误: 配置文件读取失败 - {e}")
                sys.exit(1)

        self.client = HunyuanClient(self.config)
        self.conversation_manager = ConversationManager(
            self.client,
            system_prompt="你是一个有用、专业的AI助手。"
        )
        self.current_session_id = "cli_session"
        self.conversation_manager.create_session(self.current_session_id)
        self.image_generator = None

    def get_image_generator(self):
        """获取图片生成器（延迟加载）"""
        if self.image_generator is None:
            if not self.config.secret_id or not self.config.secret_key:
                print("错误: 图片生成需要配置 secret_id 和 secret_key")
                print("请在 config.json 中添加:")
                print('  "secret_id": "你的SecretId",')
                print('  "secret_key": "你的SecretKey"')
                return None

            try:
                from hunyuan_image import HunyuanImageGenerator
                self.image_generator = HunyuanImageGenerator(
                    self.config.secret_id,
                    self.config.secret_key
                )
            except ImportError as e:
                print(f"错误: 请安装腾讯云SDK: pip install tencentcloud-sdk-python")
                print(f"详情: {e}")
                return None

        return self.image_generator

    def print_welcome(self):
        """打印欢迎信息"""
        print("=" * 60)
        print("       腾讯云混元大模型 CLI 交互工具")
        print("=" * 60)
        print("命令:")
        print("  /clear   - 清除当前会话历史")
        print("  /new     - 开始新会话")
        print("  /image <描述> - 生成图片")
        print("  /quit    - 退出程序")
        print("  /help    - 显示帮助信息")
        print("=" * 60)
        print()

    def process_command(self, user_input: str) -> bool:
        """
        处理特殊命令

        Args:
            user_input: 用户输入

        Returns:
            如果是命令返回True，否则返回False
        """
        if user_input.startswith("/"):
            command_parts = user_input.split(maxsplit=1)
            command = command_parts[0].lower()

            if command == "/quit":
                print("感谢使用，再见！")
                return True

            elif command == "/clear":
                self.conversation_manager.clear_session(self.current_session_id)
                print("会话已清除")
                return True

            elif command == "/new":
                self.current_session_id = f"session_{id(object())}"
                self.conversation_manager.create_session(self.current_session_id)
                print("新会话已创建")
                return True

            elif command == "/help":
                self.print_welcome()
                return True

            elif command == "/image":
                if len(command_parts) < 2:
                    print("用法: /image <图片描述>")
                    print("示例: /image 一只可爱的猫咪在花园里玩耍")
                    return True

                prompt = command_parts[1]
                self.generate_image(prompt)
                return True

            else:
                print(f"未知命令: {command}")
                return True

        return False

    def generate_image(self, prompt: str):
        """生成图片"""
        generator = self.get_image_generator()
        if generator is None:
            return

        print(f"\n正在生成图片: {prompt}")
        print("请稍候...")

        try:
            result = generator.generate_image_lite(
                prompt=prompt,
                resolution="1024:1024"
            )

            if result.get("success") and result.get("image_url"):
                print(f"\n图片生成成功!")
                print(f"图片URL: {result['image_url']}")

                save_dir = os.path.join(BASE_DIR, "generated_images")
                os.makedirs(save_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"hunyuan_{timestamp}.png"
                save_path = os.path.join(save_dir, filename)

                generator.save_image(result["image_url"], save_path)
                print(f"已保存到: {save_path}")
            else:
                print(f"生成失败: {result}")

        except Exception as e:
            print(f"生成图片时出错: {e}")

    def chat_loop(self):
        """主对话循环"""
        self.print_welcome()

        while True:
            try:
                user_input = input("\n你: ").strip()

                if not user_input:
                    continue

                if self.process_command(user_input):
                    continue

                print("\n助手: ", end="", flush=True)

                full_response = ""
                for chunk in self.conversation_manager.stream_send_message(
                    self.current_session_id,
                    user_input
                ):
                    print(chunk, end="", flush=True)
                    full_response += chunk

                print()

            except KeyboardInterrupt:
                print("\n\n正在退出...")
                break

            except Exception as e:
                print(f"\n错误: {e}")

    def run_simple(self, prompt: str) -> str:
        """
        简单对话接口

        Args:
            prompt: 用户输入

        Returns:
            助手回复
        """
        return self.conversation_manager.send_message(
            self.current_session_id,
            prompt
        )


def main():
    """主函数"""
    cli = HunyuanCLI()

    if len(sys.argv) > 1:
        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            print("用法: python hunyuan_cli.py")
            print("       python hunyuan_cli.py <问题>")
            return

        if len(sys.argv) > 2 and sys.argv[1] == "-c":
            config = HunyuanConfig(api_key=sys.argv[2])
            client = HunyuanClient(config)
            response = client.simple_chat(" ".join(sys.argv[3:]))
            print(response)
            return

        response = cli.run_simple(" ".join(sys.argv[1:]))
        print(f"\n助手: {response}")
    else:
        cli.chat_loop()


if __name__ == "__main__":
    main()