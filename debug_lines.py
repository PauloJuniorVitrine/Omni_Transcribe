from pathlib import Path
path = Path('src/interfaces/http/app.py')
text = path.read_text(encoding='utf-8').splitlines()
for idx in (140,150,154,160):
    if idx <= len(text):
        print(idx, text[idx-1])
