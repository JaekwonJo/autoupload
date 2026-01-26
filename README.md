# 🌊 Flow Veo Vision Bot (Final Ver)

> **Auto-Upload Automation for Flow/Sora**
> *Automate your creative workflow with precision, human-like behavior, and bulletproof reliability.*

![Status](https://img.shields.io/badge/Status-Final_Ver-success)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)

## 🏆 Final Version Features (V2)
This version represents the **Final Stable Release**. It includes strict safety rules to prevent errors and a professional HUD interface.

### ✨ New in Final Ver
- **Human Action HUD**: A detailed dashboard showing the bot's internal state (Fatigue, Typo Probability, Hesitation, Focus Loss) in real-time.
- **Strict Input Safety**:
  - **No Random Clicks**: The bot never clicks randomly. Clicks are reserved *only* for the "Submit" button.
  - **Shift+Space/Enter**: Prevents accidental IME toggling or premature sending.
- **Silent Launch**: `Flow_Start.vbs` launches the bot without any distracting black console windows.
- **Separate Log Window**: A dedicated, large window to view logs and prompt previews comfortably.

## 🚀 Quick Start

### 1. Installation
Run **`1_필수라이브러리_설치.bat`** (Only needed once).

### 2. Execution (Silent)
Double-click **`Flow_Start.vbs`**. 
*(Or use `2_오토_프로그램_실행.bat` if you prefer).*

### 3. Setup
1. **Prompts**: Edit `flow_prompts.txt` (separated by `|||`).
2. **Coordinates**: 
   - Click "⬛ 입력창" -> Drag to select text box.
   - Click "⬛ 생성 버튼" -> Drag to select submit button.
3. **AFK Area**: Click "🟩 딴짓(AFK)" -> Select a safe area (e.g., desktop wallpaper) for mouse idling.

## 🛠️ Core Features

### 📊 Dashboard & HUD
- **Dark UI**: Professional Dracula-themed interface.
- **Live Monitor**: Watch "Personality", "Mood", and detailed stats (Fatigue, Typos) change in real-time.

### 🛡️ Ultimate Safety
- **Anti-IME**: Bruteforce checks to ensure English input.
- **Zombie Slayer**: Kills old processes on startup.
- **FailSafe**: Move mouse to top-left to emergency stop.

### 🎭 Human-Like Behavior
- **AFK Mode**: Mouse moves and scrolls (no clicks) during wait times.
- **Random Speed**: Typing speed varies naturally.
- **Reporting**: Detailed session logs saved to `logs/`.

## 📂 File Structure
- `flow/flow_auto_v2.py`: Main application (UI & Logic).
- `flow/human_behavior_v2.py`: Behavior engine (Strict Rules).
- `Flow_Start.vbs`: Silent Launcher.
- `2_오토_프로그램_실행.bat`: Backup Launcher.

---
*Maintained by Jaekwon Jo*