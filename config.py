# import os
# from pydantic_settings import BaseSettings

# class Config(BaseSettings):
#     # Модель и vLLM (Gemma)
#     MODEL_NAME: str = "google/gemma-2-9b-it"
#     VLLM_API_BASE: str = "http://localhost:8000/v1"
#     VLLM_API_KEY: str = "EMPTY"
    
#     # Лимиты для Gemma (консервативно для качества экстракции)
#     CONTEXT_LIMIT: int = 8192
#     THRESHOLD_PERCENT: float = 0.20  # 20% - если файл больше, режем на чанки
#     CHUNK_SIZE_PERCENT: float = 0.15 # 15% - размер одного чанка
#     CHUNK_OVERLAP: int = 600        # Перекрытие для связки разорванных ключей
    
#     # Конкурентность vLLM
#     MAX_CONCURRENT_REQUESTS: int = 5 
    
#     # Retry Policy
#     MAX_RETRIES: int = 3
#     RETRY_DELAY: int = 2

#     class Config:
#         env_file = ".env"

# cfg = Config()
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

class Config(BaseSettings):
    # Модель и Ollama
    # Важно: убедись, что сделал `ollama run gemma2:9b` (или твою версию)
    MODEL_NAME: str = "gemma3:4b" # Или "gemma2:2b" / "gemma2:27b"
    VLLM_API_BASE: str = "http://localhost:11434/v1" 
    VLLM_API_KEY: str = "ollama" # Ollama игнорирует ключ, но поле не должно быть пустым
    
    # Лимиты для Ollama (обычно 8192)
    CONTEXT_LIMIT: int = 60000
    THRESHOLD_PERCENT: float = 0.20
    CHUNK_SIZE_PERCENT: float = 0.15
    CHUNK_OVERLAP: int = 600
    
    MAX_CONCURRENT_REQUESTS: int = 2 # Для локальной машины лучше не ставить много
    
    MAX_RETRIES: int = 2
    RETRY_DELAY: int = 2
    LOG_LEVEL: str = "DEBUG"

    class Config:
        env_file = ".env"

cfg = Config()
logging.basicConfig(
    level=cfg.LOG_LEVEL,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

runnable_config = RunnableConfig(
    recursion_limit=50,
    max_concurrency=5
)