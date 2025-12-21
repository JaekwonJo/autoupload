# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2025-12-22 (Mon)
> **Current Stage:** 🛠️ Maintenance & Stabilization

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to Sora/Flow web interfaces using visual recognition and coordinate control.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Selenium (Chrome Debugging).

## 🧩 Current Decisions & Architecture
- **Config:** JSON-based configuration (`flow_config.json`) for coordinates and prompts.
- **Persistence:** Local file storage for prompt slots (`flow_prompts.txt`).
- **Safety:** "Keep-Awake" (Insomnia) mode prevents sleep during operation.
- **Execution:** Batch file launchers for ease of use.

## ✅ Resolved (Today's Fixes)
- **[Critical] Startup Crash**: Fixed `flow_auto.py` crashing immediately due to `AttributeError: 'FlowVisionApp' object has no attribute 'load_config'`. Refactored `load_config` to a global function.
- **[Critical] UI Restoration**: Restored missing `_build_ui` method and separated it from `on_stop` logic which was malformed.
- **[Launcher] Silent Failures**: Modified `2_오토_프로그램_실행.bat` to remove hardcoded Tcl/Tk paths causing environment conflicts and added `pause` to show errors instead of closing immediately.
- **[Launcher] Python Path**: Forced usage of standard `python` command instead of `pythonw` for better debug visibility.

## 🚧 Next Steps
1. **Verification**: User to confirm the fix works in their specific environment.
2. **Feature Expansion**: Consider adding image recognition (OpenCV) for smarter button detection.
3. **Refactoring**: Clean up the legacy code in `Flow_Project` folder if it's no longer used.

## 🐛 Known Issues
- **Environment Sensitivity**: The bot relies heavily on screen coordinates. If the browser window moves or resizes, coordinates need re-capturing.
- **Dependencies**: Requires `pyautogui`, `pyperclip`, `pynput` (managed via `4_긴급수리.bat`).
