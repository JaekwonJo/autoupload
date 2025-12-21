# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2025-12-22 (Mon)
> **Current Stage:** ✨ Polishing & UX Optimization

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to Sora/Flow web interfaces using visual recognition and coordinate control.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Selenium (Chrome Debugging).

## 🧩 Current Decisions & Architecture
- **Config:** JSON-based configuration (`flow_config.json`) for coordinates and prompts.
- **Persistence:** Local file storage for prompt slots (`flow_prompts.txt`).
- **Safety:** "Keep-Awake" (Insomnia) mode prevents sleep during operation.
- **Execution:** Silent Batch launcher (`2_오토_프로그램_실행.bat`) using `pythonw` to hide console window.
- **Cleanliness:** Unused legacy files moved to `_Unused_Backup/` for a minimal workspace.

## ✅ Resolved (Today's Fixes)
- **[Critical] Startup Crash**: Refactored `load_config` to a global function and restored `_build_ui`.
- **[UX] Dual Window Removal**: Modified launcher to use `pythonw`, ensuring only the GUI window is visible.
- **[Cleanup] Workspace Organization**: Moved all irrelevant files (legacy Sora scripts, logs, old bat files) to `_Unused_Backup/`.
- **[Design] Icon Enhancement**: Generated a new high-quality, "luxurious & cute" gradient icon with a heart motif.

## 🚧 Next Steps
1. **User Feedback**: Monitor mouse movement speed and click accuracy.
2. **Notification System**: Add sound alerts or desktop notifications upon task completion.
3. **Refinement**: Permanently delete `_Unused_Backup/` after user confirmation of stability.

## 🐛 Known Issues
- **Environment Sensitivity**: Coordinates still need re-capturing if the target window moves.
- **Icon Visibility**: On some Windows versions, icon cache might need refreshing to see the new heart icon.
