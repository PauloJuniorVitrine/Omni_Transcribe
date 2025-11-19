import ast
from pathlib import Path
text = Path('src/interfaces/http/app.py').read_text(encoding='utf-8-sig')
module = ast.parse(text)
for node in ast.walk(module):
    if isinstance(node, ast.Name) and node.id == '_filter_logs':
        print('found reference at', node.lineno)
