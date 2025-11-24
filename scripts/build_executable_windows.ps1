# Build TranscribeFlow executable via PyInstaller (Windows)
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

# Usamos o spec para incluir src/ no sys.path e empacotar templates/assets/perfis.
pyinstaller --noconfirm --clean TranscribeFlow.spec
