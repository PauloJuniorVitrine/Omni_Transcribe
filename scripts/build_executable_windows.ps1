# Build TranscribeFlow executable via PyInstaller (Windows)
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --name TranscribeFlow launcher_gui.py
