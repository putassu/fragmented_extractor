import asyncio
import logging
import json
import operator
from typing import Annotated, List, Dict, Union
from langgraph.graph import StateGraph, END

import config, utils, prompts
# Импортируем провайдер 
from llm_provider import get_model_by_name 

logger = logging.getLogger("FFPA.graph")

class ExtractionState(Dict):
    """Состояние, наследуемое от мастер-агента"""
    model: str # <--- ТЕПЕРЬ МОДЕЛЬ ТУТ
    user_prompt: str
    files_metadata: List[Dict] # [{filename, filepath}]
    generated_schema: Dict
    primary_key: Union[str, List[str]]
    calculable_fields: List[str]
    raw_results: Annotated[List[Dict], operator.add]
    final_data: List[Dict]
    needs_sandbox: bool
    user_mapping: Dict

# модель создается внутри ask_llm_with_retry

async def ask_llm_with_retry(model_name: str, prompt: str, node_name: str):
    """
    Берет модель из провайдера по имени. 
    Если имени нет в реестре — упадет здесь.
    """
    # Динамическая инициализация под конкретный запрос
    llm = get_model_by_name(model_name)
    
    for attempt in range(config.cfg.MAX_RETRIES):
        logger.info(f"[{node_name}] Call {model_name} (Attempt {attempt+1})")
        
        try:
            res = await llm.ainvoke(prompt)
            parsed = utils.robust_json_parser(res.content)
            
            if parsed is not None:
                return parsed
                
            logger.warning(f"[{node_name}] JSON parse error. Content: {res.content[:100]}...")
        except Exception as e:
            logger.error(f"[{node_name}] Connection error: {e}")
            
        await asyncio.sleep(1)
        
    raise ValueError(f"Модель {model_name} не смогла вернуть JSON в узле {node_name}")

async def schema_node(state: ExtractionState):
    logger.info("--- NODE: SCHEMA GENERATION ---")
    
    # Читаем кусочек первого файла для примера
    with open(state['files_metadata'][0]['filepath'], 'r', encoding='utf-8') as f:
        sample = f.read(5000)
    
    prompt = prompts.SCHEMA_GEN_SYSTEM.format(
        user_prompt=state['user_prompt'], 
        sample_text=sample
    )
    
    # ПЕРЕДАЕМ МОДЕЛЬ ИЗ STATE
    meta = await ask_llm_with_retry(state['model'], prompt, "SchemaGen")
    
    return {
        "generated_schema": meta.get('schema', {}),
        "primary_key": meta.get('primary_key', 'id'),
        "calculable_fields": meta.get('calc_fields', []),
        "user_mapping": meta.get('user_mapping', {}),
        "needs_sandbox": len(meta.get('calc_fields', [])) > 0
    }

async def map_extraction_node(state: ExtractionState):
    logger.info(f"--- NODE: MAP EXTRACTION (Chunking enabled) ---")
    
    # Лимиты из конфига
    threshold = config.cfg.CONTEXT_WINDOW * config.cfg.CHUNK_THRESHOLD
    all_tasks = []

    async def process_chunk(chunk_text, filename, chunk_idx):
        prompt = prompts.EXTRACTION_SYSTEM.format(
            filename=f"{filename}_p{chunk_idx}",
            primary_key=state['primary_key'],
            schema=json.dumps(state['generated_schema'], ensure_ascii=False),
            text=chunk_text
        )
        data = await ask_llm_with_retry(state['model'], prompt, f"Extract:{filename}")
        
        if isinstance(data, dict): data = [data]
        for item in data: item['source_filename'] = filename
        return data

    for file_meta in state['files_metadata']:
        with open(file_meta['filepath'], 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        # ЛОГИКА ЧАНКИНГА (10% контекста)
        if utils.count_tokens_est(full_text) > threshold:
            chunks = utils.get_text_chunks(
                full_text, 
                config.cfg.CONTEXT_WINDOW, 
                config.cfg.CHUNK_SIZE, 
                config.cfg.CHUNK_OVERLAP
            )
            logger.info(f"File {file_meta['filename']} split into {len(chunks)} chunks")
        else:
            chunks = [full_text]

        for i, chunk in enumerate(chunks):
            all_tasks.append(process_chunk(chunk, file_meta['filename'], i))

    # Выполняем асинхронно
    results = await asyncio.gather(*all_tasks)
    
    # Собираем плоский список
    flat_results = [item for sublist in results for item in sublist]
    return {"raw_results": flat_results}

async def reduce_node(state: ExtractionState):
    pk = state.get('primary_key', 'id')
    pk_list = [pk] if isinstance(pk, str) else pk
    raw = state.get('raw_results', [])
    
    logger.info(f"--- REDUCER START (Items: {len(raw)}) ---")
    
    # Алгоритмическая склейка (из utils)
    final = utils.sequence_reduce(raw, pk_list)
    
    return {"final_data": final}

# Сборка графа
workflow = StateGraph(ExtractionState)
workflow.add_node("schema_gen", schema_node)
workflow.add_node("map_extract", map_extraction_node)
workflow.add_node("reduce", reduce_node)
workflow.set_entry_point("schema_gen")
workflow.add_edge("schema_gen", "map_extract")
workflow.add_edge("map_extract", "reduce")
workflow.add_edge("reduce", END)
app = workflow.compile()
