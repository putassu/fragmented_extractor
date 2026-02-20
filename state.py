from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
import operator

# Заглушка состояния Мастер-агента
class MasterState(TypedDict):
    history: List[Any]
    user_id: str
    current_status: str
    global_model: str

# Состояние нашего FEA-агента
class FEAState(MasterState):
    # Входные данные
    user_prompt: str
    files_metadata: List[Dict[str, str]] # [{'filename':..., 'filepath':...}]
    
    # Промежуточные данные
    generated_schema: Dict[str, Any]
    user_key_mapping: Dict[str, str]
    needs_sandbox: bool
    sandbox_instructions: str
    
    # Результаты (Annotated для накопления результатов из параллельных узлов)
    raw_extracted_data: Annotated[List[Dict], operator.add]
    final_reduced_data: List[Dict]
    
    errors: List[str]
