# Python-Tool-for-Evaluation-of-recorded-data-from-ECU
Automation solution that combines CAPL scripting for bus signal manipulation with Python-based analysis of ECU-recorded Byte Soup files. The goal is to build an end-to-end automated testing framework that can systematically set bus signals data across multiple cycles and validate the results through intelligent data parsing.


## 🧩 Structure
- **CAPL/** → Multi-protocol signal generator for CANoe (currently imlemented for CAN, CAN-FD)
- **Python/** → Automation control, SSH to ECU, and data analytics
- **Reports/** → Output logs and reports generated as HTML file

---

## ⚙️ Setup
1. Install **Vector CANoe** and place `MultiSignal.can`, `MultiSignal_test.can` in CAN Network and `MultiSignal_FD.can`, `MultiSignal_test_FD.can` in CAN_FD network in the simulation setup.

2. Install Python 3.11+ and dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Activate virtual environment
4. Run `python ssh_qns_controller.py`

5. View report in **Reports/analysis_report.html**
