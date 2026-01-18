# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-16 (Fri) - Ultimate Update
> **Current Stage:** 🚀 V2 Stable Release (Typing Mode + Anti-IME + WSL Optimized)

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input).

## 🧩 Current Decisions & Architecture
- **Input Method:** Reverted to **Typing Mode (`write`)** to avoid bot detection (Google captcha), but enhanced with **Bruteforce IME Check** (10 retries) to prevent Korean typos.
- **File Structure:** Migrated to `flow_auto_v2.py` and `human_behavior_v2.py` to evade zombie processes.
- **Safety:** Auto-kill zombie processes (`python.exe`) on startup.
- **Humanizer:** Advanced Bezier curves, random speed (burst/slow), AFK mode with safe playground area.
- **Environment:** Configured `.wslconfig` to limit WSL memory usage to 6GB for better system performance.

## ✅ Resolved (Today's Fixes)
- **[Critical] Korean IME Typo Fix:** Implemented robust clipboard-based IME detection (10 retries + Shift/Space/Hangul key spam) before typing.
- **[Critical] Zombie Process Kill:** Added auto-kill logic in batch script to prevent old "typing bots" from interfering.
- **[Feature] AFK Mode:** Added "User Away Mode" where the mouse idles/moves safely in a designated area (No clicks).
- **[Feature] Speed Slider:** Added real-time speed control slider (x0.5 ~ x10.0) with random variation per prompt.
- **[Feature] Sound Effects:** Added sound notifications for start (`Ding!`), finish (`Ta-da!`), and countdown (`Tick...`).
- **[System] WSL Optimization:** Auto-generated `.wslconfig` to cap WSL memory at 6GB.

## 🚧 Next Steps
1. **Long-term Monitoring**: Watch if "Typing Mode" triggers any captchas over 10+ hours.
2. **Sound Customization**: Allow users to toggle sound effects on/off.
3. **Multi-slot Expansion**: Allow running multiple slots sequentially.

## 🐛 Known Issues
- **None critical**: The "Zombie" issue is resolved by the new launcher script.
