# 🌊 Flow Veo Vision Bot (Ultimate V2)

> **Auto-Upload Automation for Flow/Sora**
> *Automate your creative workflow with precision, human-like behavior, and bulletproof reliability.*

![Status](https://img.shields.io/badge/Status-V2_Stable-success)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)

## 📖 Introduction
This project automates the submission of prompts to Flow/Sora web interfaces. It features a "Vision Bot" approach with **advanced human behavior simulation** (Bezier curves, random typos, variable speed) and **anti-detection measures**.

## 🚀 Quick Start

### 1. Installation
Run **`1_필수라이브러리_설치.bat`** if it's your first time.

### 2. Execution
Double-click **`2_오토_프로그램_실행.bat`**.
*Tip: This launcher automatically kills any zombie processes to ensure a clean start.*

### 3. Setup (First Run)
1. **Prompts**: Edit `flow_prompts.txt` (separated by `|||`).
2. **Coordinates**: Click "⬛ 입력창" and drag to select the text box. Click "⬛ 버튼" for the submit button.
3. **AFK Area (Optional)**: Click "🟩 딴짓(AFK)" and select a safe area (like the desktop wallpaper) for the mouse to play in during wait times.

## 🛠️ Key Features (V2 Update)

### 📊 Detailed Reporting (New!)
- **Auto-Logging**: Automatically saves a detailed session report (`logs/Report_...txt`) after completion.
- **Performance Stats**: Tracks total time, average speed per scene, and individual prompt durations.
- **Metadata**: Records which prompt file was used and exact timestamps.

### 🛡️ Ultimate Safety
- **Anti-IME Typing**: Uses advanced **Clipboard Detection** (10 retries) to ensure English input before typing.
- **Zombie Slayer**: Automatically terminates old bot processes on startup to prevent conflicts.
- **FailSafe**: Move mouse to the top-left corner to instantly emergency stop.
- **System Optimized**: WSL2 memory usage limited to 6GB via `.wslconfig`.

### 🎭 Human-Like Behavior
- **AFK Mode**: Mouse moves, scrolls, and idles in a safe area while waiting (No clicks).
- **Random Speed**: Typing speed varies per prompt (Burst mode vs Slow mode).
- **Speed Slider**: Real-time control to adjust the base speed (x0.5 ~ x10.0).
- **Sound Effects**: Audio feedback for start, finish, and countdown events.

## 📂 File Structure
- `flow/flow_auto_v2.py`: The main brain (V2).
- `flow/human_behavior_v2.py`: The behavior engine (Typing logic, Physics movement).
- `flow_config_final.json`: User settings.
- `2_오토_프로그램_실행.bat`: Smart launcher.

---
*Maintained by Jaekwon Jo*