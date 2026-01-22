# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-20 (Tue) - Reporting Update
> **Current Stage:** 📊 V3 UI Overhaul & Ultimate Stability

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
- **[UI] Dark Dashboard:** Complete UI redesign with progress bars, live monitor, and Dracula theme.
- **[Feature] Relay Mode:** Automatically chains multiple prompt slots for extended operation.
- **[Feature] Sound Control:** Added toggle to mute all sound effects.
- **[Fix] Black Screen Crash:** Fixed `tk.LabelFrame` padding error and WSL `winsound` compatibility.
- **[Fix] Anti-Korean Toggle:** Implemented strict `Shift` release logic before `Space` to prevent IME switching.
- **[Fix] Navigation:** Restored First/Prev/Next/Last prompt navigation buttons.
- **[Docs] Gemini Protocol:** Updated `gemini 설명서.md` to strictly enforce "Continuous Engagement" (No goodbyes).

## 🚧 Next Steps
1. **Long-term Monitoring**: Watch if "Typing Mode" triggers any captchas over 10+ hours.
2. **Telegram Integration**: Send notification to phone when job is done or error occurs.
3. **Smart Resume**: Resume from the last crashed point if interrupted.

## 🐛 Known Issues
- **None**: All critical and UX issues have been resolved.