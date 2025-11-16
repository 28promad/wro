# 🧑‍💻 Copilot Instructions for Databot Rover Dashboard

## Big Picture Architecture
- **Main Components:**
  - `main_pi.py`: Rover controller, reads sensors, pushes data to `rover_data_service.py`.
  - `rover_data_service.py`: Thread-safe in-memory buffer for sensor data, provides data to web server.
  - `web_app.py`: Flask server with WebSocket and REST API, serves dashboard UI in `templates/`.
  - `web_app_simple.py`: Flask server (polling only, no WebSocket), fallback for simpler deployments.
  - `templates/dashboard.html`: Main dashboard UI (WebSocket), `dashboard_simple.html` for polling.
- **Data Flow:** Sensors → `main_pi.py` → `rover_data_service.py` → `web_app.py` → Dashboard (browser)
- **Service Boundaries:** Sensor reading, data buffering, web serving, and UI are separated for reliability and clarity.

## Developer Workflows
- **Quick Start:**
  - Follow `QUICKSTART.md` for 4-step install and run.
  - Start `main_pi.py` and `web_app.py` (see docs for details).
- **Testing:**
  - Test files: `test_*.py` in root and subfolders (e.g., `test_comm_pi.py`, `test_imu.py`).
  - No unified test runner; run individual test files as scripts.
- **Debugging:**
  - Use print/log statements in files.
  - Check dashboard status bar and connection indicator for live status.

## Project-Specific Conventions
- **Documentation:**
  - Extensive docs: `README_INDEX.md` (index), `SYSTEM_OVERVIEW.md`, `ARCHITECTURE.md`, `DASHBOARD_README.md`, `, `BEFORE_AFTER.md`.
  - Always reference the index for navigation.
- **Patterns:**
  - Data is always pushed from controller to service, never pulled directly by UI.
  - WebSocket preferred for dashboard updates; fallback to polling if needed.
  - Thread-safety is enforced in `rover_data_service.py`.
- **Error Handling:**
  - Controller (`main_pi.py`) continues running if disconnected; robust to network failures.
  - Troubleshooting sections in docs for common issues.

## Integration Points & Dependencies
- **External:**
  - Flask (web server), WebSocket (real-time updates), systemd (production Pi setup).
  - Python dependencies in `requirements.txt`.
- **Cross-Component Communication:**
  - Sensor data flows via shared buffer (`rover_data_service.py`).
  - Web server reads from buffer, broadcasts to UI.

## Key Files & Directories
- `main_pi.py`, `rover_data_service.py`, `web_app.py`, `templates/dashboard.html`
- Docs: `README_INDEX.md`, `QUICKSTART.md`, `SYSTEM_OVERVIEW.md`, `ARCHITECTURE.md`, `DASHBOARD_README.md`, `DEPLOYMENT.md`, `BEFORE_AFTER.md`
- Tests: `test_*.py` in root and subfolders

## Example Patterns
- To add a new sensor: update `main_pi.py` to read it, push to `rover_data_service.py`, update dashboard UI if needed.
- To add a new dashboard feature: update `dashboard.html` and corresponding API/WebSocket logic in `web_app.py`.

---

**For more details, always start with `README_INDEX.md`.**

---

*Update this file if major architecture or workflow changes occur.*
