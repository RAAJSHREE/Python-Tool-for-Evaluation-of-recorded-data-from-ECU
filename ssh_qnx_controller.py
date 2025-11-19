import os
import time
import subprocess
import pandas as pd
import paramiko
from scp import SCPClient

# ===========================================================
#                    CONFIGURATION
# ===========================================================
CANOE_HOST = "10.210.53.161"
CANOE_USER = r"APAC\LC36KOR" # Modify the user name
CANOE_PASS = password # Change the password in ""

REMOTE_BAT = r"C:\Users\Public\Documents\Vector\CANoe\Projects\CAN_500kBaud_2ch\bat\canoe_simulation.bat"  # Remote Bat location
REMOTE_BLF_PATH = r"C:/Users/Public/Documents/Vector/CANoe/Projects/CAN_500kBaud_2ch/Logs/SignalReport.blf" #generated blf file
LOCAL_BLF_PATH = r"./logs/SignalReport.blf" # Local path to copy the generated blf for decoding

PSEXEC_PATH = r"C:\Users\rbh2cob\Documents\PSTools\PsExec.exe"

CYCLES = 20
DELAY_MS = 200


# ===========================================================
#                    BLF READER (from byte_soup)
# ===========================================================
from can.io import BLFReader
try:
    from can.io.blf import CompressedBLFReader
except Exception:
    CompressedBLFReader = None


def read_blf_to_dataframe(filepath, max_msgs=None):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"BLF file not found: {filepath}")

    messages = []
    reader_classes = [BLFReader]
    if CompressedBLFReader:
        reader_classes.append(CompressedBLFReader)

    last_error = None

    for reader in reader_classes:
        try:
            print(f"[INFO] Trying reader: {reader.__name__}")
            with reader(filepath) as log:
                for index, msg in enumerate(log):
                    if max_msgs and index >= max_msgs:
                        break

                    arb_id = getattr(msg, "arbitration_id", getattr(msg, "id", None))
                    data_bytes = getattr(msg, "data", getattr(msg, "payload", []))

                    messages.append({
                        "timestamp": getattr(msg, "timestamp", None),
                        "id": hex(arb_id) if arb_id is not None else None,
                        "dlc": getattr(msg, "dlc", getattr(msg, "length", None)),
                        "is_fd": getattr(msg, "is_fd", False),
                        "channel": getattr(msg, "channel", None),
                        "direction": (
                            "Tx" if getattr(msg, "is_tx", False)
                            else "Rx" if getattr(msg, "is_rx", False)
                            else None
                        ),
                        "data": list(data_bytes)
                    })
            break

        except Exception as e:
            last_error = e
            print(f"[WARN] {reader.__name__} failed: {e}")

    if not messages:
        raise RuntimeError(f"BLF reader failed. Last error: {last_error}")

    df = pd.DataFrame(messages)
    print(f"[OK] Loaded {len(df)} messages from {filepath}")
    return df


# ===========================================================
#                    SSH / SCP FUNCTIONS
# ===========================================================
def scp_get(remote_path, local_path):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print(f"[INFO] Connecting to remote host {CANOE_HOST}...")
    ssh.connect(CANOE_HOST, username=CANOE_USER, password=CANOE_PASS, timeout=10)

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    print("[INFO] Copying BLF file from remote...")
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(remote_path, local_path)

    ssh.close()
    print(f"[OK] File saved to {local_path}")


# ===========================================================
#                 CANOE SIMULATION CONTROL
# ===========================================================
def start_canoe_measurement():
    print("[INFO] Starting CANoe measurement via PsExec...")

    cmd = [
        PSEXEC_PATH,
        f"\\\\{CANOE_HOST}",
        "-u", CANOE_USER,
        "-p", CANOE_PASS,
        "-i",
        REMOTE_BAT
    ]

    subprocess.run(cmd, check=True)
    print("[INFO] CANoe launched successfully.")


# ===========================================================
#                   ANALYSIS FUNCTION
# ===========================================================
def analyze_blf(blf_path):
    print("[INFO] Analyzing BLF...")

    df = read_blf_to_dataframe(blf_path)
    os.makedirs("reports", exist_ok=True)

    decoded_csv = "./reports/decoded.csv"
    df.to_csv(decoded_csv, index=False)

    signals = ["EngineSpeed", "Torque", "CoolantTemp"]
    analysis = pd.DataFrame({
        "Signal": signals,
        "Min": [df.get(sig, pd.Series()).min() for sig in signals],
        "Max": [df.get(sig, pd.Series()).max() for sig in signals],
        "Mid": [(df.get(sig, pd.Series()).min() + df.get(sig, pd.Series()).max())/2 for sig in signals]
    })

    analysis_csv = "./reports/signal_analysis.csv"
    analysis.to_csv(analysis_csv, index=False)

    print("[OK] Analysis completed.")
    return {"decoded": decoded_csv, "analysis": analysis_csv}


# ===========================================================
#                           MAIN
# ===========================================================
def main():
    # 1. Start CANoe
    start_canoe_measurement()

    # 2. Wait for measurement to finish
    wait_sec = (CYCLES * DELAY_MS / 1000.0) + 5
    print(f"[INFO] Waiting {wait_sec:.1f} seconds for CAPL cycles...")
    time.sleep(wait_sec)

    # 3. Copy BLF
    scp_get(REMOTE_BLF_PATH, LOCAL_BLF_PATH)

    # 4. Analyze
    report_paths = analyze_blf(LOCAL_BLF_PATH)
    print("[DONE] Reports generated:", report_paths)


if __name__ == "__main__":
    main()
