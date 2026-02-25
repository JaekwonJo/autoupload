# 🔨 Build Log

## 2026-02-25 (Wed) - Slot Auto Sync + Calendar Scheduler UX
- **Success**:
  - Added requested "auto sync newly added prompt slot files" workflow.
  - Replaced difficult manual datetime typing with a calendar/time picker UI.
- **Changes**:
  - **Prompt Slot Sync (`flow_auto_v2.py`)**:
    - Added `🔄 슬롯 동기화` button near slot controls.
    - Added `on_sync_slots()` to scan `flow_prompts_slot_*.txt` / `flow_prompts_slot*.txt` and append missing files to `prompt_slots`.
    - Added duplicate-safe naming with `_make_unique_slot_name()`.
  - **One-time Scheduled Start (`flow_auto_v2.py`)**:
    - Added schedule config keys (`scheduled_start_enabled`, `scheduled_start_at`).
    - Added reserve-wait runtime state (`scheduled_waiting`, `scheduled_start_ts`).
    - Start flow now supports immediate start or wait-until-reserved-time start.
  - **UX Upgrade (Calendar Picker)**:
    - Replaced manual schedule typing with read-only display + `📅 달력 선택`.
    - Added month navigation, day click selection, hour/minute spinboxes, and quick actions (`오늘`, `현재+5분`, `현재+30분`, `예약 지우기`).
- **Validation**:
  - Syntax compile check passed via local venv Python:
    - `./.venv_wsl/bin/python -m py_compile flow/flow_auto_v2.py`

## 2026-01-28 (Wed) - Final Gold Edition (The "Perfect" Update)
- **Success**: 
  - **Final Polish**: Added requested navigation and renaming features to reach 100% completion.
- **Changes**:
  - **Navigation (`flow_auto_v2.py`)**:
    - Added `on_first`, `on_last`, and `on_jump_to` methods.
    - Updated UI with ⏮, ⏭ buttons and clickable status label for jumping to specific numbers.
  - **Slot Management**:
    - Implemented `on_rename_slot` with a ✏️ UI button to allow changing slot names (e.g., "Slot 1" -> "Daily Task").
  - **Documentation**: Synchronized all state and log files for project completion.
- **Result**: User confirmed 100% satisfaction. VS Code closed.

---
## 2026-01-27 (Tue) - Final V2 Release (Strict Rules & HUD)
- **Success**: Overnight test with 60 items completed successfully.
- **Features**: No Random Clicks, HUD Dashboard, Separate Log Window, Modern Icon.

---
## 2026-01-26 (Mon) - UI Dashboard & Launcher Overhaul
- **Features**: Silent VBS launcher, Professional Icon, Detailed real-time metrics.
