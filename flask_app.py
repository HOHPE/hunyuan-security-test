
from flask import Flask, render_template, request, jsonify, session
from hunyuan_config import HunyuanConfig
from hunyuan_client import HunyuanClient
from hunyuan_image import HunyuanImageGenerator
from hunyuan_logger import initialize_logger, get_module_logger
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'hunyuan_secret_key'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


logger_config = {
    "level": "INFO",
    "console": {"enabled": True, "level": "DEBUG", "colored": True},
    "file": {
        "enabled": True,
        "level": "INFO",
        "path": os.path.join(BASE_DIR, "logs", "hunyuan.log"),
        "max_size": 5 * 1024 * 1024,
        "backup_count": 5,
        "rotation": "size",
        "retention_days": 7
    }
}
initialize_logger(logger_config)
logger = get_module_logger("flask_app")


CONFIG_PATH = os.path.join(BASE_DIR, "config.json")


GENERATED_IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warn("配置文件不存在，使用默认配置")
        return {}

config = load_config()
logger.info("配置加载完成", extra={"config_keys": list(config.keys())})

@app.route('/')
def index():
    logger.info("访问首页")
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')

    if not message:
        logger.warn("收到空消息请求")
        return jsonify({'error': '请输入消息'}), 400

    logger.info("收到聊天请求", extra={"message_length": len(message)})
    start_time = datetime.now()

    try:
        if message.strip().startswith('/image'):
            logger.info("检测到图片生成命令")
            return generate_image(message.strip()[7:].strip())

        hunyuan_config = HunyuanConfig(**config)
        client = HunyuanClient(hunyuan_config)
        response = client.simple_chat(message)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("对话请求完成", extra={
            "response_length": len(response),
            "duration": f"{duration:.3f}s"
        })

        return jsonify({
            'success': True,
            'response': response,
            'type': 'text'
        })
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"对话请求失败: {str(e)}", extra={
            "duration": f"{duration:.3f}s",
            "error_type": type(e).__name__
        })
        return jsonify({
            'success': False,
            'error': str(e),
            'type': 'error'
        })

@app.route('/api/generate_image', methods=['POST'])
def generate_image(prompt=None):
    data = request.json if request.json else {}
    prompt = prompt or data.get('prompt', '')

    if not prompt:
        logger.warn("收到空图片生成请求")
        return jsonify({'error': '请输入图片描述'}), 400

    if not config.get('secret_id') or not config.get('secret_key'):
        logger.error("API密钥未配置")
        return jsonify({
            'success': False,
            'error': '需要配置 secret_id 和 secret_key 才能生成图片',
            'type': 'error'
        })

    logger.info("开始生成图片", extra={"prompt_length": len(prompt)})
    start_time = datetime.now()

    try:
        generator = HunyuanImageGenerator(
            config['secret_id'],
            config['secret_key']
        )

        result = generator.generate_image_lite(
            prompt=prompt,
            resolution="1024:1024"
        )

        duration = (datetime.now() - start_time).total_seconds()

        if result.get('success') and result.get('image_url'):
            os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hunyuan_{timestamp}.png"
            save_path = os.path.join(GENERATED_IMAGES_DIR, filename)
            generator.save_image(result["image_url"], save_path)

            logger.info("图片生成成功", extra={
                "image_url": result['image_url'],
                "local_path": save_path,
                "duration": f"{duration:.3f}s"
            })

            return jsonify({
                'success': True,
                'image_url': result['image_url'],
                'local_path': save_path,
                'prompt': prompt,
                'type': 'image'
            })
        else:
            logger.warn(f"图片生成返回异常结果: {result}")
            return jsonify({
                'success': False,
                'error': str(result),
                'type': 'error'
            })
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"图片生成失败: {str(e)}", extra={
            "duration": f"{duration:.3f}s",
            "error_type": type(e).__name__
        })
        return jsonify({
            'success': False,
            'error': str(e),
            'type': 'error'
        })

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    global config

    if request.method == 'POST':
        logger.info("收到配置更新请求")
        config = request.json
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info("配置已保存")
        return jsonify({'success': True, 'message': '配置已保存'})

    return jsonify(config)

@app.route('/api/security/test', methods=['GET'])
def security_test_info():

    logger.info("获取安全测试用例列表")
    try:
        from hunyuan_security import SecurityTestRunner, AttackType, SeverityLevel

        runner = SecurityTestRunner()

        test_cases_info = []
        for tc in runner.test_cases:
            test_cases_info.append({
                'case_id': tc.case_id,
                'name': tc.name,
                'description': tc.description,
                'attack_type': tc.attack_type.value,
                'severity': tc.severity.name,
                'test_prompt': tc.test_prompt,
                'expected_behavior': tc.expected_behavior
            })

        logger.info(f"返回{len(test_cases_info)}个测试用例")
        return jsonify({
            'success': True,
            'total_cases': len(test_cases_info),
            'test_cases': test_cases_info
        })
    except Exception as e:
        logger.error(f"获取测试用例失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/security/run', methods=['POST'])
def run_security_test():

    logger.info("开始运行安全测试")
    start_time = datetime.now()

    try:
        from hunyuan_security import SecurityTestRunner

        if not config.get('secret_id') or not config.get('secret_key'):
            logger.error("API密钥未配置，无法运行安全测试")
            return jsonify({
                'success': False,
                'error': '需要配置 secret_id 和 secret_key 才能运行安全测试'
            })

        generator = HunyuanImageGenerator(
            config['secret_id'],
            config['secret_key']
        )

        runner = SecurityTestRunner(image_generator=generator)
        report = runner.run_all_tests()

        results_path = os.path.join(BASE_DIR, "security_test_results.json")
        runner.save_results(results_path)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"安全测试完成", extra={
            "total_tests": report['summary']['total_tests'],
            "passed": report['summary']['passed'],
            "failed": report['summary']['failed'],
            "duration": f"{duration:.1f}s"
        })

        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"安全测试执行失败: {str(e)}", extra={
            "duration": f"{duration:.1f}s",
            "error_type": type(e).__name__
        })
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/security/report', methods=['GET'])
def get_security_report():

    logger.info("获取安全测试报告")
    try:
        report_path = os.path.join(BASE_DIR, "security_test_results.json")
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        return jsonify({
            'success': True,
            'report': report
        })
    except FileNotFoundError:
        logger.warn("测试报告文件不存在")
        return jsonify({
            'success': False,
            'error': '暂无测试报告，请先运行安全测试'
        })
    except Exception as e:
        logger.error(f"读取测试报告失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("腾讯混元生图系统启动")
    logger.info("=" * 50)
    app.run(host='0.0.0.0', port=8501, debug=True)
