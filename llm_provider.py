
import logging
from config import cfg
from langchain_openai import ChatOpenAI
import httpx

logger = logging.getLogger("FFPA")
_shared_client = httpx.AsyncClient(verify=False, proxy=None)

def get_model_by_name(model_name: str, temperature: float = 0):
    # Проверяем наличие в реестре
    if model_name not in cfg.MODELS_REGISTRY:
        error_msg = f"КРИТИЧЕСКАЯ ОШИБКА: Модель '{model_name}' не зарегистрирована в MODELS_REGISTRY!"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    creds = cfg.MODELS_REGISTRY[model_name]
    logger.info(f"Инициализация модели: {model_name} (Endpoint: {creds['url']})")
    
    return ChatOpenAI(
        model=model_name,
        openai_api_base=creds["url"],
        openai_api_key=creds["key"],
        temperature=temperature,
        http_async_client =_shared_client,
        max_tokens=16000
    )
