from typing import Annotated, List, Dict, Union, Optional
from typing_extensions import TypedDict
import operator

class ExtractionState(TypedDict):
    # Входные данные от Мастера
    user_prompt: str
    files_metadata: List[Dict] # [{filename, filepath, total_tokens}]
    
    # Внутреннее состояние
    generated_schema: Dict
    primary_key: str
    calculable_fields: List[str]
    user_mapping: Dict
    
    # Результаты (Annotated для накопления в параллельных узлах)
    raw_results: Annotated[List[Dict], operator.add]
    final_data: List[Dict]
    
    # Служебные поля
    needs_sandbox: bool
    errors: List[str]
    status: str
