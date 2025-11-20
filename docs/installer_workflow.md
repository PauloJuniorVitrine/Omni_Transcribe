## Installer Workflow for TranscribeFlow

### Goal
Provide a single, professional experience for building the Windows installer, staging it under `Downloads\transcribeflow-installer`, running the automated suite, and opening the web interface with minimal manual steps.

### Prerequisites (CoCoT)
- Windows 10/11 x64 (checked by the PowerShell helpers).
- Valid runtime secrets stored locally inside `scripts/install.local.env`:
  ```
  OPENAI_API_KEY=sk-...
  CREDENTIALS_SECRET_KEY=<32-byte-url-safe>
  ```
  Do **not** commit this file. Keep it private.
- Source tree with `run_with_gui.ps1`, `test_installer_flow.ps1`, and `prepare_installer.ps1`.

### Workflow steps (ToT)
1. **Prepare the installer bundle**
   ```
   powershell -ExecutionPolicy Bypass scripts\prepare_installer.ps1
   ```
   This downloads dependencies if needed, copies `dist\TranscribeFlow.exe` into `Downloads\transcribeflow-installer`, and resets the staging folder.
2. **Run the installer test suite**
   ```
   powershell -ExecutionPolicy Bypass scripts\test_installer_flow.ps1
   ```
   The suite:
   * Loads `scripts/install.local.env`.
   * Invokes `run_with_gui.ps1` with `-ForceResetCredentials`.
   * Waits until `TranscribeFlow.exe` launches and responds at `http://localhost:8000`.
   * Cleans up the processes after verification.
3. **Start the GUI manually (optional)**
   ```
   powershell -ExecutionPolicy Bypass scripts\run_with_gui.ps1
   ```
   or double-click the **TranscribeFlow GUI** shortcut created by the script.

### Automation checks (ReAct)
- `prepare_installer.ps1` ensures the `Downloads\transcribeflow-installer` directory always contains the latest `.exe`, so no manual copy is necessary.
- `test_installer_flow.ps1` asserts that the real GUI is reachable, mirroring the exact code path used by customers.
- Any failure displays a clear error and aborts to prevent shipping a broken bundle.

### CI Recommendation
Use a Windows runner with secrets (`OPENAI_API_KEY`, `CREDENTIALS_SECRET_KEY`) to run:
```
- powershell -ExecutionPolicy Bypass scripts\prepare_installer.ps1
- powershell -ExecutionPolicy Bypass scripts\test_installer_flow.ps1
```
This keeps the release pipeline deterministic and ensures zero regression.

### Visualization

```
[install.local.env] --> prepare_installer.ps1 --> test_installer_flow.ps1 --> run_with_gui.ps1 --> http://localhost:8000
                                                        \___________________________________________/
                                                                     tests Sanitized GUI
```
