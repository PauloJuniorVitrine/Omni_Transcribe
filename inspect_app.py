import sys, types, inspect
from pathlib import Path
root = Path.cwd()
src = root / "src"
for path in (str(root), str(src)):
    if path not in sys.path:
        sys.path.insert(0, path)
ps = types.ModuleType("pydantic_settings")
class BaseSettings: ...
class SettingsConfigDict(dict): ...
ps.BaseSettings = BaseSettings
ps.SettingsConfigDict = SettingsConfigDict
sys.modules["pydantic_settings"] = ps
python_multipart = types.ModuleType("python_multipart")
python_multipart.__version__ = "0.0"
sys.modules["python_multipart"] = python_multipart
multipart = types.ModuleType("multipart")
def parse_options_header(value):
    return value, {}
multipart.parse_options_header = parse_options_header
sys.modules["multipart"] = multipart
python_multipart.multipart = multipart
import interfaces.http.app as http_app
print("Loaded from", http_app.__file__)
print(inspect.getsource(http_app.job_detail))
