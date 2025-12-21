# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2025-12-22 (Mon)
> **Current Stage:** 🚀 Stable Release Candidate

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to Sora/Flow web interfaces using visual recognition and coordinate control.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Selenium (Chrome Debugging).

## 🧩 Current Decisions & Architecture
- **Config:** JSON-based configuration (`flow_config.json`) for coordinates and prompts.
- **Persistence:** Local file storage for prompt slots (`flow_prompts.txt`).
- **Safety:** "Keep-Awake" (Insomnia) mode prevents sleep during operation.
- **Execution:** Robust Silent Launcher (`2_오토_프로그램_실행.bat`) using `pyw` for console-free operation.
- **Cleanliness:** Unused legacy files moved to `_Unused_Backup/` for a minimal workspace.

## ✅ Resolved (Today's Fixes)
- **[Critical] Startup Crash**: Refactored `load_config` to a global function and restored `_build_ui` in `flow_auto.py`.
- **[UX] Dual Window Removal**: Implemented `pythonw`/`pyw` based launcher to prevent the persistent console window.
- **[Launcher] Silent Launch Robustness**: Fixed a "flash and close" crash in the launcher by simplifying the Python detection logic to prefer `pyw -3`.
- **[Cleanup] Workspace Organization**: Moved all irrelevant files (legacy Sora scripts, logs, old bat files) to `_Unused_Backup/`.
- **[Design] Icon Enhancement**: Generated a new high-quality, "luxurious & cute" gradient icon with a heart motif.

## 🚧 Next Steps
1. **Mouse Accuracy Check**: Verify if the random human-like movement needs calibration for different screen resolutions.
2. **Audio Feedback**: Implement sound notifications for task completion (e.g., "Ding!").
3. **Final Cleanup**: Delete `_Unused_Backup/` once the user confirms total stability for a few days.

## 🐛 Known Issues
- **Environment Sensitivity**: Coordinates still need re-capturing if the target window moves.
- **Icon Cache**: Windows Explorer might delay showing the new icon until a restart or cache clear.