import json
from agno.knowledge import Knowledge
with open('kn_dir.json', 'w') as f:
    json.dump([m for m in dir(Knowledge) if not m.startswith('_')], f, indent=2)
