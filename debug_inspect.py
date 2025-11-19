import sys, types
from pathlib import Path
import inspect
root = Path(r"c:/Users/User/Desktop/Nova pasta/PROJETOS/Omni Transcribe").resolve()
src = root / 'src'
for path in (str(root), str(src)):
    if path not in sys.path:
        sys.path.insert(0, path)
ps = types.ModuleType('pydantic_settings')
class BaseSettings: ...
class SettingsConfigDict(dict): ...
ps.BaseSettings = BaseSettings
ps.SettingsConfigDict = SettingsConfigDict
sys.modules['pydantic_settings'] = ps
pm = types.ModuleType('python_multipart')
pm.__version__ = '0.1.0'
sys.modules['python_multipart'] = pm
import interfaces.http.app as app
print(inspect.getsource(app.job_detail))
print('--- filter function ---')
print(inspect.getsource(app._filter_logs))
