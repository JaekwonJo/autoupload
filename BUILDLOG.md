# 🔨 Build Log

## 2026-01-20 (Tue) - V3 UI Overhaul & Critical Stability Fixes
- **Error**: Black screen crash immediately after launch; Korean characters appearing during typing.
- **Cause**: 
  1. `tk.LabelFrame` does not support `padding` option (Python version mismatch).
  2. `winsound` module missing on WSL/Linux environments.
  3. Rapid typing caused accidental `Shift+Space` (IME toggle).
  4. Navigation buttons (First/Prev/Next/Last) were missing in V2 design.
- **Fix**: 
  - **UI**: Replaced all `tk.LabelFrame` with `ttk.LabelFrame`.
  - **Compatibility**: Added `try-except` block for `winsound` to support WSL.
  - **Typing Engine**: Implemented `Shift` key release safety logic before pressing `Space`.
  - **Navigation**: Restored First/Prev/Next/Last prompt navigation buttons.
- **Features Added**:
  - **Dark Dashboard UI**: Complete redesign with Dracula theme, progress bars, and live status monitor.
  - **Live Monitor**: Visualizes current Persona, Mood, and Typing Speed in real-time.
  - **Sound Toggle**: Checkbox to mute all sound effects.
  - **Relay Mode**: Option to automatically chain multiple prompt slots (e.g., run 3 files in a row).
  - **Crash Catcher**: Prevents window from closing on error; saves traceback to `CRASH_LOG.txt`.
- **Result**: A stable, beautiful, and feature-rich automation bot that works on both Windows and WSL without crashes.

---
## 2026-01-20 (Tue) - Detailed Reporting System
- **Error**: N/A (Feature Request)
- **Cause**: User requested detailed logging of session times and per-scene durations.
- **Fix**: 
  - `flow/flow_auto_v2.py`: Implemented `save_session_report` to generate detailed `.txt` logs.
  - `flow/flow_auto.py`: Backported the reporting logic to the V1 script for consistency.
  - `gemini 설명서.md`: Added strict "Continuous Engagement" rules (No goodbye phrases).
  - **Logic**: Captures start/end times, calculates duration per scene, and saves file with prompt metadata.
- **Result**: Automated generation of `Report_filename_timestamp.txt` in `logs/` folder after every run.

---
## 2026-01-16 (Fri) - The "Anti-IME" War & System Optimization
- **Error**: Korean characters (`ㄴ8 ㅖ개...`) appearing instead of English prompts despite multiple IME detection fixes.
- **Cause**: 
  1. `Shift+Space` accidentally triggering IME toggle during typing.
  2. "Zombie" processes of old versions persisting in background.
  3. "Paste Mode" was rejected due to bot detection risks.
- **Fix**: 
  - **Zombie Slayer**: Updated `2_오토...bat` to `taskkill` all python processes before starting.
  - **Code Migration**: Moved all logic to `flow_auto_v2.py` to ensure fresh execution.
  - **Input Method**: Reverted to **Typing Mode** but added a 10-try bruteforce IME check before starting.
  - **System**: Created `.wslconfig` to limit WSL2 memory usage to 6GB.
- **Features Added**:
  - **AFK Mode**: Mouse moves/scrolls in safe area during wait time (No clicks).
  - **Speed Slider**: Real-time typing speed adjustment with random variance.
  - **Sound Effects**: Added `winsound` beeps for start, finish, and countdown.
- **Result**: Safe, human-like typing with zero Korean typos, robust stability, and optimized system memory.

---
## 2025-12-22 (Mon) - Critical Stabilization & UX
- **Error**: Program crashed immediately with a black screen; Debugging revealed `AttributeError: load_config` and malformed class structure.
- **Cause**: Incomplete code editing or corruption in `flow_auto.py`.
- **Fix**: 
  - `flow/flow_auto.py`: Extracted `load_config`, reconstructed `_build_ui`.
  - `2_오토_프로그램_실행.bat`: Simplified detection logic to use `pyw -3` directly for reliable silent launch.
- **Result**: Application starts correctly, loads config, UI renders, and console window is hidden.