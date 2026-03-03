# 🔨 Build Log

## 2026-03-03 (Tue) - Ver.01 Release (Tray + Pause/Resume + Installer)
- **Success**:
  - Added tray-minimize close behavior and tray exit confirmation.
  - Added `일시정지/재개` flow that keeps browser session alive.
  - Added one-touch bootstrap launcher for PCs without Python.
  - Added installer wizard scripts for final distribution (`.exe` setup builder).
- **Changes**:
  - **Runtime/UI (`flow_auto_v2.py`)**:
    - Added app version label: `2026-03-03 Ver.01`.
    - Added pause/resume runtime state and control buttons.
    - Kept existing stop as full stop (browser close).
  - **One-touch launch**:
    - Added `0_원터치_설치+실행.bat`.
    - Updated `Flow_Start.vbs`, `run_silent.vbs` to prefer embedded runtime.
    - Added `FlowVeo_실행.bat` for installer shortcut entry.
  - **Installer build**:
    - Added Inno Setup script: `release/installer/FlowVeo_20260303_Ver01.iss`
    - Added build helper: `release/build_installer.bat`
    - Added release guide: `release/배포_가이드_20260303_Ver01.md`

## 2026-02-28 (Sat) - Reserved Start Strict Wait (No Mouse Move Before Time)
- **Success**:
  - Added strict reservation wait behavior exactly as requested.
  - Before reserved time, mouse no longer moves and automation does not begin.
- **Changes**:
  - **Reserved Wait Runtime (`flow_auto_v2.py`)**:
    - In `_tick()`, idle mouse wandering now runs only when `scheduled_waiting == False`.
    - During reservation waiting, 30s countdown alert popup is also suppressed.
    - At reserved timestamp, existing start flow proceeds normally.
- **Documentation**:
  - Added Korean update guide: `기능_업데이트_설명서.md`.
- **Validation**:
  - Syntax compile check passed:
    - `python3 -m py_compile flow/flow_auto_v2.py`

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
