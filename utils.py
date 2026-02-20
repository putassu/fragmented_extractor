import json, re, logging
import pandas as pd
from typing import List, Dict, Any

logger = logging.getLogger("FFPA.utils")

import json
import re

def count_tokens_est(text: str) -> int:
    """
    Грубая оценка количества токенов. 
    Для кириллицы/смешанного текста берем ~3.5 символа на токен.
    """
    if not text:
        return 0
    return len(text) // 3

def get_text_chunks(text: str, context_window: int, chunk_size_pct: float, overlap: int) -> list[str]:
    """
    Разбивает текст на куски, основываясь на проценте от контекстного окна.
    """
    # Вычисляем размер чанка в символах (примерно)
    # Если окно 60 000 токенов, а CHUNK_SIZE 0.15 -> чанк 9 000 токенов -> ~27 000 символов
    tokens_per_chunk = int(context_window * chunk_size_pct)
    chars_per_chunk = tokens_per_chunk * 3 
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chars_per_chunk
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chars_per_chunk - overlap)
        
        # Защита от бесконечного цикла, если overlap слишком большой
        if start >= text_len or chars_per_chunk <= overlap:
            break
            
    return chunks

def robust_json_parser(text: str):
    """Очистка ответа LLM от маркдауна и парсинг JSON"""
    try:
        # Убираем блоки ```json ... ```
        clean_text = re.sub(r'```json\s*|\s*```', '', text).strip()
        return json.loads(clean_text)
    except Exception:
        # Пытаемся найти что-то похожее на JSON массив или объект
        match = re.search(r'(\{.*\}|\[.*\])', clean_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                return None
        return None

# def sequence_reduce(raw_results: list[dict], pk_fields: list[str]) -> list[dict]:
#     """
#     Склеивает результаты экстракции по первичным ключам.
#     """
#     merged = {}
    
#     for item in raw_results:
#         # Создаем уникальный ключ для записи на основе PK
#         pk_value = tuple(str(item.get(f, "")).strip().lower() for f in pk_fields)
        
#         if pk_value not in merged:
#             merged[pk_value] = item
#         else:
#             # Обновляем поля, если они пустые (простейшая склейка)
#             for k, v in item.items():
#                 if not merged[pk_value].get(k):
#                     merged[pk_value][k] = v
                    
#     return list(merged.values())
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
