# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-20 (Tue) - Reporting Update
> **Current Stage:** 📊 V2 Feature Enhancement (Logging & Reporting)

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input).

## 🧩 Current Decisions & Architecture
- **Input Method:** Reverted to **Typing Mode (`write`)** to avoid bot detection (Google captcha), but enhanced with **Bruteforce IME Check** (10 retries) to prevent Korean typos.
- **File Structure:** Migrated to `flow_auto_v2.py` and `human_behavior_v2.py` to evade zombie processes.
- **Safety:** Auto-kill zombie processes (`python.exe`) on startup.
- **Humanizer:** Advanced Bezier curves, random speed (burst/slow), AFK mode with safe playground area.
- **Reporting:** Detailed session logs saved to `logs/` with prompt filename, timestamps, and per-scene duration.

## ✅ Resolved (Today's Fixes)
- **[Feature] Detailed Session Report:** Added a comprehensive reporting system that saves a text file to `logs/` after each session.
- **[Feature] Metadata Logging:** Reports now include the prompt filename, start/end times, and total duration.
- **[Feature] Scene Timing:** Logs the exact duration (in seconds) for each individual prompt generation.
- **[Feature] Summary Popup:** Enhanced the completion message box to show a quick summary of the session stats.
- **[Docs] Gemini Protocol:** Updated `gemini 설명서.md` to strictly enforce "Continuous Engagement" (No goodbyes).

## 🚧 Next Steps
1. **Long-term Monitoring**: Watch if "Typing Mode" triggers any captchas over 10+ hours.
2. **Sound Customization**: Allow users to toggle sound effects on/off.
3. **Multi-slot Expansion**: Allow running multiple slots sequentially.

## 🐛 Known Issues
- **None critical**: The "Zombie" issue is resolved by the new launcher script.