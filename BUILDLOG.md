# 🔨 Build Log

## 2026-01-16 (Fri) - The "Anti-IME" War & Ultimate V2
- **Error**: Korean characters (`ㄴ8 ㅖ개...`) appearing instead of English prompts despite multiple IME detection fixes.
- **Cause**: 
  1. `Shift+Space` accidentally triggering IME toggle during typing.
  2. "Zombie" processes of old versions persisting in background and typing concurrently with new version.
- **Fix**: 
  - **Nuclear Option**: Replaced character typing with **Word-by-Word Copy & Paste**.
  - **Zombie Slayer**: Updated `2_오토...bat` to `taskkill` all python processes before starting.
  - **Code Migration**: Moved all logic to `flow_auto_v2.py` to ensure fresh execution.
- **Features Added**:
  - **AFK Mode**: Mouse moves/scrolls in safe area during wait time (No clicks).
  - **Speed Slider**: Real-time typing speed adjustment with random variance.
  - **Random Submit**: 50/50 chance of `Enter` vs `Click` for submission.
- **Result**: 100% English input guarantee, robust stability, and enhanced human-like behavior.

---
## 2025-12-22 (Mon) - Critical Stabilization & UX
- **Error**: Program crashed immediately with a black screen; Debugging revealed `AttributeError: load_config` and malformed class structure.
- **Cause**: Incomplete code editing or corruption in `flow_auto.py`.
- **Fix**: 
  - `flow/flow_auto.py`: Extracted `load_config`, reconstructed `_build_ui`.
  - `2_오토_프로그램_실행.bat`: Simplified detection logic to use `pyw -3` directly for reliable silent launch.
- **Result**: Application starts correctly, loads config, UI renders, and console window is hidden.
