"""
简单的API测试，验证配置是否正确
"""
import os
import json
from hunyuan_image import HunyuanImageGenerator

# 获取脚本所在目录，确保路径正确
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    """加载配置"""
    config_path = os.path.join(BASE_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def main():
    print("="*60)
    print("腾讯混元API测试")
    print("="*60)
    
    config = load_config()
    
    secret_id = config.get('secret_id')
    secret_key = config.get('secret_key')
    
    if not secret_id or not secret_key:
        print("错误: 未配置 secret_id 和 secret_key")
        print("请检查 config.json 文件")
        return 1
    
    print("\n配置信息:")
    print(f"  Secret ID: {secret_id[:10]}...")
    print(f"  Secret Key: {secret_key[:10]}...")
    
    print("\n初始化图片生成器...")
    try:
        generator = HunyuanImageGenerator(secret_id, secret_key)
        print("[OK] 图片生成器初始化成功")
    except Exception as e:
        print(f"[FAIL] 图片生成器初始化失败: {e}")
        return 1
    
    print("\n测试生成一张安全的图片...")
    try:
        result = generator.generate_image_lite(
            prompt="一只可爱的小猫在阳光下玩耍",
            resolution="512:512"
        )
        
        if result.get("success"):
            print("[OK] 图片生成成功!")
            print(f"  Image URL: {result.get('image_url', '')[:60]}...")
            
            save_dir = os.path.join(BASE_DIR, "generated_images")
            os.makedirs(save_dir, exist_ok=True)
            filename = "test_api_success.png"
            save_path = os.path.join(save_dir, filename)
            
            generator.save_image(result["image_url"], save_path)
            print(f"  图片已保存到: {save_path}")
        else:
            print(f"[FAIL] 图片生成失败: {result}")
            
    except Exception as e:
        print(f"[FAIL] API调用异常: {e}")
        return 1
    
    print("\n" + "="*60)
    print("API测试成功！")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
