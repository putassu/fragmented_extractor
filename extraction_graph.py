import asyncio
import logging
import json
from typing import Annotated, List, Dict
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

import config, utils, prompts

logger = logging.getLogger("FFPA.graph")

class ExtractionState(Dict):
    user_prompt: str
    files_metadata: List[Dict]
    generated_schema: Dict
    primary_key: str
    calculable_fields: List[str]
    raw_results: Annotated[List[Dict], operator.add]
    final_data: List[Dict]
    needs_sandbox: bool

llm = ChatOpenAI(
    model=config.cfg.MODEL_NAME,
    openai_api_base=config.cfg.VLLM_API_BASE,
    openai_api_key=config.cfg.VLLM_API_KEY,
    temperature=0
)

async def ask_llm_with_retry(prompt: str, node_name: str):
    """Оболочка для LLM с логированием и попытками парсинга."""
    for attempt in range(config.cfg.MAX_RETRIES):
        logger.info(f"[{node_name}] LLM Call (Attempt {attempt+1}/{config.cfg.MAX_RETRIES})")
        
        # ЛОГ ИНПУТА (первые 200 символов)
        logger.debug(f"[{node_name}] Input: {prompt[:200]}...")
        
        res = await llm.ainvoke(prompt)
        
        # ЛОГ АУТПУТА
        logger.debug(f"[{node_name}] Raw Output: {res.content[:200]}...")
        
        parsed = utils.robust_json_parser(res.content)
        if parsed is not None:
            return parsed
        
        logger.warning(f"[{node_name}] Failed to parse JSON on attempt {attempt+1}")
        await asyncio.sleep(1)
        
    raise ValueError(f"Failed to get valid JSON from LLM in node {node_name}")

async def schema_node(state: ExtractionState):
    logger.info("--- NODE: SCHEMA GENERATION ---")
    with open(state['files_metadata'][0]['filepath'], 'r', encoding='utf-8') as f:
        sample = f.read(3000)
    
    prompt = prompts.SCHEMA_GEN_SYSTEM.format(
        user_prompt=state['user_prompt'], 
        sample_text=sample
    )
    
    meta = await ask_llm_with_retry(prompt, "SchemaGen")
    
    return {
        "generated_schema": meta['schema'],
        "primary_key": meta['primary_key'],
        "calculable_fields": meta.get('calculable_fields', []),
        "needs_sandbox": len(meta.get('calculable_fields', [])) > 0
    }

async def map_extraction_node(state: ExtractionState):
    logger.info(f"--- NODE: MAP EXTRACTION ({len(state['files_metadata'])} files) ---")
    
    async def process_file(file_meta):
        with open(file_meta['filepath'], 'r', encoding='utf-8') as f:
            text = f.read()
        
        # В этой версии для простоты берем файл целиком, 
        # если он > контекста — тут должна быть логика чанкинга из utils.chunk_text
        prompt = prompts.EXTRACTION_SYSTEM.format(
            filename=file_meta['filename'],
            primary_key=state['primary_key'],
            schema=json.dumps(state['generated_schema'], ensure_ascii=False),
            text=text
        )
        
        data = await ask_llm_with_retry(prompt, f"Extract:{file_meta['filename']}")
        if isinstance(data, dict): data = [data]
        for item in data: item['source_filename'] = file_meta['filename']
        return data

    tasks = [process_file(f) for f in state['files_metadata']]
    results = await asyncio.gather(*tasks)
    return {"raw_results": [item for sublist in results for item in sublist]}
 

async def reduce_node(state: ExtractionState):
    pk = state.get('primary_key', 'id')
    pk_list = [pk] if isinstance(pk, str) else pk
    
    raw = state.get('raw_results', [])
    
    # Логируем для отладки
    logger.info(f"--- REDUCER START ---")
    logger.info(f"PK Fields: {pk_list}")
    logger.info(f'вызываю reducer node c raw = {str(raw)[:300]}')
    # Вызов обновленной функции
    final = utils.sequence_reduce(raw, pk_list)
    
    logger.info(f"Entities after merge: {len(final)}")
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
