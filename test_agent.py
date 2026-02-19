import asyncio
import os
import sys
import logging

# Фикс путей
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

async def test():
    from extraction_graph import app
    
    # Создаем тестовые данные (имитируем фрагменты одного документа)
    test_dir = os.path.join(current_dir, "temp_logs_test")
    os.makedirs(test_dir, exist_ok=True)
    
    path1 = os.path.join(test_dir, "doc_part1.txt")
    path2 = os.path.join(test_dir, "doc_part2.txt")
    
    with open(path1, "w", encoding="utf-8") as f:
        f.write("Протокол №ABC-777. Объект: Мост. Дата: 2024-05-01.")
    
    with open(path2, "w", encoding="utf-8") as f:
        f.write("Ответственный: Петров. Статус: Пройдено.")

    inputs = {
        "user_prompt": "Собери данные по протоколу, объекту и ответственному.",
        "files_metadata": [
            {"filename": "ABC-777", "filepath": path1},
            {"filename": "ABC-777", "filepath": path2}
        ],
        "raw_results": [],
        "errors": []
    }

    logging.getLogger("FFPA").info("Starting test agent execution...")
    
    result = await app.ainvoke(inputs)
    import json
    logging.getLogger("FFPA").info(f"ФИНАЛЬНЫЙ РЕЗУЛЬТАТ \n {json.dumps(result.get('final_data'), indent=2, ensure_ascii=False)}")
    
    # print("\n" + "="*50)
    # print("ФИНАЛЬНЫЙ JSON (РЕЗУЛЬТАТ):")
    # import json
    # print(json.dumps(result.get('final_data'), indent=2, ensure_ascii=False))
    # print("="*50)

if __name__ == "__main__":
    asyncio.run(test())
