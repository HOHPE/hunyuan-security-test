
import os
from hunyuan_config import HunyuanConfig
from hunyuan_client import HunyuanClient
from hunyuan_conversation import ConversationManager


def example_basic_chat():

    print("=" * 50)
    print("示例1: 基础对话")
    print("=" * 50)

    config = HunyuanConfig(
        api_key=os.getenv("HUNYUAN_API_KEY", "your-api-key"),
        model="hunyuan-turbos-latest"
    )
    client = HunyuanClient(config)

    response = client.simple_chat("你好，请介绍一下你自己")
    print(f"用户: 你好，请介绍一下你自己")
    print(f"助手: {response}")
    print()


def example_with_system_prompt():

    print("=" * 50)
    print("示例2: 带系统提示词的对话")
    print("=" * 50)

    config = HunyuanConfig.from_env()
    client = HunyuanClient(config)

    system_prompt = "你是一位专业的Python编程导师，用简洁易懂的语言解释技术概念。"
    response = client.simple_chat(
        "什么是装饰器？",
        system_prompt=system_prompt
    )
    print(f"用户: 什么是装饰器？")
    print(f"助手: {response}")
    print()


def example_stream_chat():

    print("=" * 50)
    print("示例3: 流式对话")
    print("=" * 50)

    config = HunyuanConfig.from_env()
    client = HunyuanClient(config)

    messages = [
        {"role": "user", "content": "用三句话解释什么是机器学习"}
    ]

    print("用户: 用三句话解释什么是机器学习")
    print("助手: ", end="")

    full_response = ""
    for chunk in client.stream_chat(messages):
        print(chunk, end="", flush=True)
        full_response += chunk

    print("\n")
    print(f"[完整回复长度: {len(full_response)} 字符]")
    print()


def example_multi_turn_conversation():

    print("=" * 50)
    print("示例4: 多轮对话")
    print("=" * 50)

    config = HunyuanConfig.from_env()
    client = HunyuanClient(config)

    messages = [
        {"role": "system", "content": "你是一个乐于助人的编程助手。"}
    ]

    questions = [
        "Python中列表和元组的区别是什么？",
        "那字典呢？",
        "它们在性能上有区别吗？"
    ]

    for question in questions:
        print(f"用户: {question}")
        response, messages = client.multi_turn_chat(messages, question)
        print(f"助手: {response}")
        print()


def example_conversation_manager():

    print("=" * 50)
    print("示例5: 会话管理器")
    print("=" * 50)

    config = HunyuanConfig.from_env()
    client = HunyuanClient(config)
    manager = ConversationManager(client)

    session_id = "user_123_session_1"

    print(f"创建会话: {session_id}")
    manager.create_session(session_id)

    print("\n--- 第一轮对话 ---")
    response1 = manager.send_message(session_id, "推荐5本编程书籍")
    print(f"用户: 推荐5本编程书籍")
    print(f"助手: {response1[:100]}...")

    print("\n--- 第二轮对话 ---")
    response2 = manager.send_message(
        session_id,
        "其中第一本的核心观点是什么？"
    )
    print(f"用户: 其中第一本的核心观点是什么？")
    print(f"助手: {response2[:100]}...")

    session_info = manager.get_session_info(session_id)
    print(f"\n会话信息: {session_info}")

    print("\n--- 清除会话 ---")
    manager.clear_session(session_id)
    print("会话已清除")


def example_custom_parameters():

    print("=" * 50)
    print("示例6: 自定义参数")
    print("=" * 50)

    config = HunyuanConfig.from_env()
    client = HunyuanClient(config)

    messages = [
        {"role": "user", "content": "写一个关于AI的短诗"}
    ]

    print("temperature=0.7 (默认):")
    response1 = client.chat(messages, temperature=0.7)
    print(f"助手: {response1['choices'][0]['message']['content']}")

    print("\ntemperature=1.2 (高随机性):")
    response2 = client.chat(messages, temperature=1.2)
    print(f"助手: {response2['choices'][0]['message']['content']}")

    print("\ntemperature=0.1 (低随机性):")
    response3 = client.chat(messages, temperature=0.1)
    print(f"助手: {response3['choices'][0]['message']['content']}")


if __name__ == "__main__":
    try:
        example_basic_chat()
        example_with_system_prompt()
        example_stream_chat()
        example_multi_turn_conversation()
        example_conversation_manager()
        example_custom_parameters()
    except Exception as e:
        print(f"错误: {e}")