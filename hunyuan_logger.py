"""
腾讯混元生图项目日志模块
======================

功能特性：
- 多级别日志记录（DEBUG、INFO、WARN、ERROR）
- 分级输出到控制台和文件系统
- 结构化JSON格式
- 可配置日志级别、输出路径、轮转策略
- 日志保留期限管理
- 高性能、低侵入设计

使用方式：
    from hunyuan_logger import get_logger
    logger = get_logger()
    logger.info("这是一条信息日志")
    logger.info("API调用", extra={"api": "chat", "duration": "1.23s"})
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON格式日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "thread": record.thread,
            "process": record.process
        }

        if self.include_extra and hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """带颜色的控制台格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m"
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        time_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"{color}[{time_str}] [{record.levelname:5}] [{record.name}] {record.getMessage()}{reset}"

class ExtraAdapter(logging.LoggerAdapter):
    """支持extra参数的日志适配器"""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        if hasattr(self, "extra") and self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

def _create_logger(name: str, config: Dict[str, Any]) -> logging.Logger:
    """创建配置好的logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    console_config = config.get("console", {})
    if console_config.get("enabled", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_config.get("level", "DEBUG").upper()))
        if console_config.get("colored", True):
            console_handler.setFormatter(ColoredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(
                "[%(asctime)s] [%(levelname)5s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
        logger.addHandler(console_handler)

    file_config = config.get("file", {})
    if file_config.get("enabled", True):
        log_path = file_config.get("path", "logs/hunyuan.log")
        log_dir = Path(log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        rotation = file_config.get("rotation", "size")
        max_size = file_config.get("max_size", 10 * 1024 * 1024)
        backup_count = file_config.get("backup_count", 7)

        if rotation == "time":
            file_handler = TimedRotatingFileHandler(
                filename=log_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8"
            )
        else:
            file_handler = RotatingFileHandler(
                filename=log_path,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding="utf-8"
            )

        file_handler.setLevel(getattr(logging, file_config.get("level", "INFO").upper()))
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

        retention_days = file_config.get("retention_days", 30)
        _cleanup_old_logs(log_path, retention_days)

    logger.propagate = False
    return logger

def _cleanup_old_logs(log_path: str, retention_days: int):
    """清理过期日志文件"""
    try:
        log_dir = Path(log_path).parent
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        for log_file in log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    log_file.unlink()
                except Exception:
                    pass
    except Exception:
        pass

_logger_instance: Optional[logging.Logger] = None
_current_config: Dict[str, Any] = {}

def initialize_logger(config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """初始化日志系统"""
    global _logger_instance, _current_config

    if config is None:
        config = {
            "level": "INFO",
            "console": {"enabled": True, "level": "DEBUG", "colored": True},
            "file": {
                "enabled": True,
                "level": "INFO",
                "path": "logs/hunyuan.log",
                "max_size": 10 * 1024 * 1024,
                "backup_count": 7,
                "rotation": "size",
                "retention_days": 30
            }
        }

    _current_config = config
    _logger_instance = _create_logger("hunyuan", config)
    return _logger_instance

def get_logger(name: str = "hunyuan") -> logging.Logger:
    """获取日志记录器"""
    global _logger_instance, _current_config

    if _logger_instance is None:
        initialize_logger(_current_config)

    if name == "hunyuan":
        return _logger_instance

    return _create_logger(name, _current_config)

def get_module_logger(module_name: str, **context) -> ExtraAdapter:
    """
    获取模块专属日志记录器（支持上下文信息）

    使用示例：
        logger = get_module_logger("hunyuan_image", session_id="123")
        logger.info("图片生成成功")
    """
    base_logger = get_logger("hunyuan")
    return ExtraAdapter(base_logger, context)

class APILogger:
    """API调用日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log(self, api_name: str, params: Dict, response: Any, duration: float):
        """记录API调用"""
        status = "success" if not isinstance(response, Exception) else "failed"
        self.logger.info(
            f"API调用: {api_name}",
            extra={
                "api_name": api_name,
                "params": params,
                "duration": f"{duration:.3f}s",
                "response_status": status
            }
        )

class SecurityTestLogger:
    """安全测试日志记录器"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log(self, test_id: str, result: str, details: Dict):
        """记录安全测试"""
        self.logger.info(
            f"安全测试: {test_id} - {result}",
            extra={
                "test_id": test_id,
                "result": result,
                "details": details
            }
        )

api_logger = None
security_logger = None

def get_api_logger() -> APILogger:
    """获取API日志记录器"""
    global api_logger
    if api_logger is None:
        api_logger = APILogger(get_logger())
    return api_logger

def get_security_test_logger() -> SecurityTestLogger:
    """获取安全测试日志记录器"""
    global security_logger
    if security_logger is None:
        security_logger = SecurityTestLogger(get_logger())
    return security_logger
