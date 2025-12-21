# 🌊 Flow Veo Vision Bot (Ultimate)

> **Auto-Upload Automation for Flow/Sora**
> *Automate your creative workflow with precision and style.*

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)

## 📖 Introduction
This project automates the submission of prompts to Flow/Sora web interfaces. It features a "Vision Bot" approach, using coordinate-based interaction and visual cues to control the browser, ensuring compatibility even when DOM-based selection fails.

## 🚀 Quick Start

### 1. Installation
Run **`4_긴급수리.bat`** (Emergency Repair) to install necessary Python dependencies (`pyautogui`, `pyperclip`, `pynput`, etc.).

### 2. Configuration
Edit **`flow_prompts.txt`** to add your prompts, separated by `|||`.
*Example:*
```text
A beautiful sunset over the ocean |||
A futuristic city with flying cars |||
A cute cat playing with a ball
```

### 3. Execution
Double-click **`2_오토_프로그램_실행.bat`**.
- The **Flow Veo** UI will appear.
- **Set Coordinates**: Click "📍 입력창 위치" (Input Box) and "📍 생성 버튼 위치" (Generate Button) to tell the bot where to click.
- **Start**: Click "🌙 조용히 시작" (Stealth Start) to begin the automation loop.

## 🛠️ Key Features
- **👻 Stealth Mode**: Operates with minimal interference.
- **☕ Insomnia Mode**: Prevents system sleep while the bot is running.
- **🎨 Modern UI**: Dark-themed Tkinter interface with real-time logs and countdowns.
- **💾 Auto-Save**: Remembers your coordinate settings and last active prompt slot.

## 📂 File Structure
- `flow/flow_auto.py`: The main brain of the bot.
- `flow_config.json`: Stores user settings (coordinates, intervals).
- `flow_prompts.txt`: Your prompt list.
- `2_오토_프로그램_실행.bat`: The primary launcher.

## ⚠️ Troubleshooting
If the program closes immediately or doesn't start:
1. Run `4_긴급수리.bat` to check dependencies.
2. Check `BUILDLOG.md` for recent fixes.
3. Ensure you are not running in a restricted environment (admin rights might be needed for input control).

---
*Maintained by Jaekwon Jo*
