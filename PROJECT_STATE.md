# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-01-27 (Tue) - Final Version (V2 Stable)
> **Current Stage:** 🏆 Final Version (Stabilized & Polished)

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input), Pillow (Icon).

## 🧩 Current Decisions & Architecture
- **Launcher**: `Flow_Start.vbs` handles the launch silently, while `2_오토_프로그램_실행.bat` provides a backup method. Both ensure no distracting console windows.
- **Strict Input Rules**: To mimic human typing perfectly and avoid errors:
  - **No Random Clicks**: Mouse clicks are strictly limited to the "Submit" action only.
  - **Shift+Space/Enter**: Spaces and newlines are typed with specific key combinations to prevent IME interference and unintended submissions.
- **HUD Interface**: The new "Human Action HUD" dashboard provides real-time visibility into the bot's internal state (Fatigue, Typo Rate, Focus Loss, etc.), replacing the simple status labels.
- **Reporting**: Detailed session logs saved to `logs/` with prompt filename, timestamps, and per-scene duration.

## ✅ Resolved (Today's Fixes)
- **[Feature] Final V2 Release:** Verified success with a 60-item overnight run.
- **[Fix] Strict Input Rules:** Implemented "No Random Click" policy and forced `Shift` logic for Space/Enter to prevent IME issues and accidental submits.
- **[Feature] HUD Dashboard:** Replaced the simple stats panel with a comprehensive "Human Action HUD" that displays real-time fatigue, typo rates, and active behavior traits.
- **[Feature] Separate Log Window:** Moved the cramped log/preview text boxes to a dedicated, large pop-up window for better readability.
- **[Design] High-Visibility Mode:** Changed AFK mode text color to Magenta/Cyan for better visibility.
- **[Asset] Modern Icon:** Updated to a futuristic hexagon "AI Eye" icon.

## 🚧 Next Steps
1. **Monitor & Maintain:** Continue using the bot for daily tasks to ensure long-term stability.
2. **Backup Strategy:** Regularly zip and backup the `flow` folder.
3. **Minor Tweaks:** Adjust specific humanization parameters (e.g., speed, pause rates) if the target platform changes its detection logic.

## 🐛 Known Issues
- None at this moment. The "Final Ver" is considered stable for production use.
