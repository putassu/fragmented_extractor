from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Данные от мастер-агента
    model: str = "gemma3:4b"                # Название модели, например "gemma-3-27" или "deepseek-r1"
    user_prompt: str          # Исходный кривой промпт пользователя
    files: List[Dict]         # [{filename: "abc.pdf", text: "...", filepath: "..."}]
    history: List[BaseMessage] # История диалога
    
    # Внутреннее состояние экстрактора (заполняется в процессе)
    primary_key: List[str]
    schema: Dict[str, Any]
    calc_fields: List[str]
    user_mapping: Dict[str, str]
    
    # Результаты
    raw_results: List[Dict]
    final_data: List[Dict]
    needs_sandbox: bool
    errors: List[str]
