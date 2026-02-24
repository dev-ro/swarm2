import json
from agno.vectordb.lancedb import LanceDb
from agno.knowledge import Knowledge
with open('v_dir.json', 'w') as f:
    json.dump([m for m in dir(LanceDb) if not m.startswith('_')], f, indent=2)
with open('k_add.json', 'w') as f:
    import inspect
    try:
        json.dump({
            "Knowledge.insert": str(inspect.signature(Knowledge.insert)),
            "Knowledge.add_content": str(inspect.signature(Knowledge.add_content)),
            "LanceDb.insert": str(inspect.signature(LanceDb.insert))
        }, f, indent=2)
    except Exception as e:
        json.dump({"error": str(e)}, f)
