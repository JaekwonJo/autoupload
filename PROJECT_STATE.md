# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-16 (Fri)
> **Current Stage:** 🚀 V2 Stable Release (Ultimate Anti-IME Edition)

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input).

## 🧩 Current Decisions & Architecture
- **Input Method:** Switched from `typewrite` to **`pyperclip` (Paste)** to prevent Korean IME issues 100%.
- **File Structure:** Migrated to `flow_auto_v2.py` and `human_behavior_v2.py` to evade zombie processes.
- **Safety:** Auto-kill zombie processes (`python.exe`) on startup.
- **Humanizer:** Advanced Bezier curves, random speed (burst/slow), AFK mode with safe playground area.

## ✅ Resolved (Today's Fixes)
- **[Critical] Korean IME Typo Fix:** Replaced all typing logic with **Word-by-Word Paste** (`Ctrl+V`). Even if Korean key is on, it pastes English correctly.
- **[Critical] Zombie Process Kill:** Added auto-kill logic in batch script to prevent old "typing bots" from interfering.
- **[Feature] AFK Mode:** Added "User Away Mode" where the mouse idles/moves safely in a designated area.
- **[Feature] Speed Slider:** Added real-time speed control slider (x0.5 ~ x10.0) with random variation per prompt.
- **[Safety] Submit Logic:** Submits via **Random (Enter OR Click)** to mimic human behavior, never double submits.

## 🚧 Next Steps
1. **Long-term Monitoring**: Watch if "paste mode" has any side effects over 10+ hours.
2. **Sound Feedback**: Add optional sound effects for "Start", "Finish", "Error".
3. **Multi-slot Expansion**: Allow running multiple slots sequentially? (Maybe later).

## 🐛 Known Issues
- **None critical**: The "Zombie" issue is resolved by the new launcher script.
