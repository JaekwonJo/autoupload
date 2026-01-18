# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-16 (Fri) - Ultimate Update
> **Current Stage:** 🚀 V2 Stable Release (Typing Mode + Anti-IME)

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input).

## 🧩 Current Decisions & Architecture
- **Input Method:** Reverted to **Typing Mode (`write`)** to avoid bot detection (Google captcha), but enhanced with **Bruteforce IME Check** (10 retries) to prevent Korean typos.
- **File Structure:** Migrated to `flow_auto_v2.py` and `human_behavior_v2.py` to evade zombie processes.
- **Safety:** Auto-kill zombie processes (`python.exe`) on startup.
- **Humanizer:** Advanced Bezier curves, random speed (burst/slow), AFK mode with safe playground area.

## ✅ Resolved (Today's Fixes)
- **[Critical] Korean IME Typo Fix:** Implemented robust clipboard-based IME detection (10 retries + Shift/Space/Hangul key spam) before typing.
- **[Critical] Zombie Process Kill:** Added auto-kill logic in batch script to prevent old "typing bots" from interfering.
- **[Feature] AFK Mode:** Added "User Away Mode" where the mouse idles/moves safely in a designated area (No clicks).
- **[Feature] Speed Slider:** Added real-time speed control slider (x0.5 ~ x10.0) with random variation per prompt.
- **[Safety] Random Submit:** Randomly chooses between **Enter** key or **Mouse Click** (50/50) to submit.
- **[Decision] Input Method:** Switching to Paste mode caused detection issues, so reverted to **Typing Mode** with enhanced safety.

## 🚧 Next Steps
1. **Long-term Monitoring**: Watch if "Typing Mode" triggers any captchas over 10+ hours.
2. **Sound Feedback**: Add optional sound effects for "Start", "Finish", "Error".
3. **Multi-slot Expansion**: Allow running multiple slots sequentially.

## 🐛 Known Issues
- **None critical**: The "Zombie" issue is resolved by the new launcher script.