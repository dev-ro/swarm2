from agno.knowledge.lancedb import LanceDbKnowledgeBase
from agno.document import Document
for attr in dir(LanceDbKnowledgeBase):
    if not attr.startswith('_'):
        print(attr)
