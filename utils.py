import json, re, logging
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger("FFPA.utils")

def robust_json_parser(text: str) -> Any:
    try:
        # Улучшенный поиск JSON: ищем самый широкий охват [ ] или { }
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        logger.error(f"Failed to parse JSON: {text[:200]}")
    return []

def sequence_reduce(raw_results: List[Dict], pk_fields: List[str]) -> List[Dict]:
    if not raw_results: return []
    
    final_data = []
    
    # 1. Сначала очистим каждый объект от явных галлюцинаций LLM, 
    # но сохраним информацию о FOLLOW_PREVIOUS
    for item in raw_results:
        # Ищем: есть ли СЛОВО "FOLLOW_PREVIOUS" хоть в одном значении объекта?
        has_follow_label = any(str(v).upper() == "FOLLOW_PREVIOUS" for v in item.values())
        
        # Проверяем, пустые ли основные PK поля
        pk_is_empty = all(not item.get(f) or str(item.get(f)).upper() == "NONE" for f in pk_fields)

        is_continuation = has_follow_label or (pk_is_empty and len(item) > len(pk_fields))

        if is_continuation and final_data:
            # Склеиваем с ПОСЛЕДНИМ объектом в списке
            last_obj = final_data[-1]
            for k, v in item.items():
                # Не переносим саму метку и служебные поля
                if v and str(v).upper() != "FOLLOW_PREVIOUS" and k not in ["PK", "pk"]:
                    # Если в оригинале пусто или null — записываем данные из чанка
                    if last_obj.get(k) is None or last_obj.get(k) == "":
                        last_obj[k] = v
        else:
            # Это новый объект. 
            # Удаляем галлюцинацию "PK": "FOLLOW_PREVIOUS", если она есть
            clean_item = {k: v for k, v in item.items() if k not in ["PK", "pk"]}
            # Если в самом PK поле стоит метка — зануляем её, чтобы не портить данные
            for f in pk_fields:
                if str(clean_item.get(f)).upper() == "FOLLOW_PREVIOUS":
                    clean_item[f] = None
            
            final_data.append(clean_item)

    return final_data