
import os
from pydantic_settings import BaseSettings
import logging
import logging
import sys

# Сначала гасим всё
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("langchain").setLevel(logging.ERROR)
import sys
from langchain_core.runnables import RunnableConfig

from pydantic_settings import BaseSettings
from typing import Dict

import sys
import logging
from typing import Dict
from pydantic_settings import BaseSettings
from langchain_core.runnables import RunnableConfig

class Config(BaseSettings):
    # 1. Реестр моделей
    #    нужно передавать в поле state['model'])
    MODELS_REGISTRY: Dict[str, Dict[str, str]] = {
        "gemma3:4b": {
            "url": "http://localhost:11434/v1",
            "key": "sk-gerwhtrnymymmmm"
        },
        "deepseek-v3": {
            "url": "http://10.0.245.11:8000/v1",
            "key": "sk-deepseek-corp"
        }
    }
    
    # 2. Параметры чанкинга
    CONTEXT_WINDOW: int = 60000
    # Когда начинать чанкинг (если файл > 20% контекста)
    CHUNK_THRESHOLD: float = 0.20  
    # Размер одного чанка (15% от контекста)
    CHUNK_SIZE: float = 0.15       
    CHUNK_OVERLAP: int = 600
    
    # 3. Лимиты и повторы
    MAX_CONCURRENT_REQUESTS: int = 2
    MAX_RETRIES: int = 2
    RETRY_DELAY: int = 2
    LOG_LEVEL: str = "DEBUG"

    class Config:
        env_file = ".env"

cfg = Config()

# Настройка логирования с использованием новых имен
logging.basicConfig(
    level=cfg.LOG_LEVEL,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Конфигурация для LangGraph
runnable_config = RunnableConfig(
    recursion_limit=50,
    max_concurrency=cfg.MAX_CONCURRENT_REQUESTS
)
