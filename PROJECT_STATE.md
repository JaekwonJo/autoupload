# 🏗️ Project State: Flow Veo Vision Bot

> **Last Updated:** 2026-02-28 (Sat) - Reserved Start Strict Wait
> **Current Stage:** 🛠️ Scheduling Precision Update
> **Latest Handoff Doc:** `CODEX_연속작업_인수인계_20260304.md`

## 📊 Project Overview
- **Type:** Desktop Automation Tool (Python, Tkinter, PyAutoGUI)
- **Goal:** Automate prompt submission to AI interfaces with extreme human-like behavior and anti-detection.
- **Key Stack:** Python 3.12+, Tkinter (UI), PyAutoGUI (Control), Pyperclip (Safe Input), Pillow (Icon).

## 🧩 Current Decisions & Architecture
- **Navigation Overhaul**: Added `First`, `Last`, and `Jump-to-Index` (via label click) for managing large prompt lists (60+ items).
- **Slot Management**: Implemented a renaming feature for prompt slots to allow user personalization.
- **Strict Input Safety**: 
  - **Zero-Click Typing**: Clicks are strictly forbidden during the typing phase.
  - **IME-Safe Keys**: `Shift+Space` for spaces and `Shift+Enter` for newlines to prevent common automation errors.
- **HUD Interface**: Real-time monitoring of internal humanization metrics (Fatigue, Typo Probability, etc.).
- **Prompt Slot Auto Sync**:
  - New button scans `flow` folder for `flow_prompts_slot_숫자.txt` and `flow_prompts_slot숫자.txt`.
  - Newly found files are automatically added to `prompt_slots`.
- **One-time Reservation Start (Specific Date/Time)**:
  - Supports delayed start at exact reserved datetime.
  - Reservation is persisted in config and resumed on app restart.
  - While waiting for reserved time, mouse stays still (no AFK wander before start).
- **Calendar-based Reservation UX**:
  - Removed hard manual typing dependency.
  - Date is picked from calendar, time via hour/minute selectors.

## ✅ Resolved (Today's Fixes)
- **[Fix] Reserved Start Strict Wait:** During reservation wait, no mouse movement occurs; automation starts only at reserved time.
- **[Feature] Slot File Auto Sync:** Added one-click sync to register newly added slot files automatically.
- **[Feature] One-time Reserved Start:** Added wait-until-reserved-time execution mode.
- **[UX] Calendar Reservation Picker:** Added calendar popup to select date/time without typing format manually.
- **[Feature] Jump to Number:** Clicking the navigation status label now opens a dialog to jump to any specific prompt number.
- **[Feature] First/Last Navigation:** Added ⏮ and ⏭ buttons for quick boundary navigation.
- **[Feature] Slot Renaming:** Added a ✏️ button to rename prompt slots, updating both the config and the UI.
- **[Fix] Input Safety Logic:** Verified that all random clicks are removed from typing/idle routines. Newline now correctly uses `Shift+Enter`.

## 🚧 Next Steps
- **Optional UX**:
  - Increase calendar button/font size for accessibility.
  - Add "everyday repeating reservation" as separate mode if requested.
- **Maintenance**:
  - Continue prompt file updates and use slot sync button when new files are added.

## 🐛 Known Issues
- None. This is the Final Gold Edition.
