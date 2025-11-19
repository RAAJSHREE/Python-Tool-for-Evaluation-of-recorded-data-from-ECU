import re
import os
import pandas as pd
from can.io import BLFReader
try:
    from can.io.blf import CompressedBLFReader
except:
    CompressedBLFReader = None
import paramiko
from scp import SCPClient
 
# ----------------------------------------------------------
# 1. READ CAPL FILES (.can) & EXTRACT EXPECTED VALUES
# ----------------------------------------------------------
CAPL_REGEX = re.compile(
    r"es\s*=\s*([0-9]+)\s*;\s*tq\s*=\s*([0-9]+)\s*;\s*tp\s*=\s*([0-9]+)",
    re.IGNORECASE
)
 
def parse_capl(path):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    matches = CAPL_REGEX.findall(txt)
 
    es, tq, tp = [], [], []
    for a, b, c in matches:
        es.append(int(a))
        tq.append(int(b))
        tp.append(int(c))
    return es, tq, tp
 
 
# ----------------------------------------------------------
# 2. BUILD EXPECTED RANGE TABLE
# ----------------------------------------------------------
def build_expected_table(es, tq, tp):
    def to_stats(values):
        return {
            "Min": min(values),
            "Max": max(values),
            "Mid": (min(values) + max(values)) / 2
        }
 
    expected = {
        "EngineSpeed": to_stats(es),
        "Torque": to_stats(tq),
        "CoolantTemp": to_stats(tp)
    }
    return expected
 
 
# ----------------------------------------------------------
# 3. READ BLF → Extract actual CAN signal values
# ----------------------------------------------------------
def read_blf(blf_path, msg_id=None):
    rows = []
 
    readers = [BLFReader]
    if CompressedBLFReader:
        readers.append(CompressedBLFReader)
 
    for reader in readers:
        try:
            with reader(blf_path) as log:
                for msg in log:
                    data = bytes(msg.data)
                    arb = msg.arbitration_id
 
                    if msg_id is not None and arb != msg_id:
                        continue
 
                    rows.append({
                        "EngineSpeed": (data[0] << 8) | data[1] if len(data) >= 2 else None,
                        "Torque": (data[2] << 8) | data[3] if len(data) >= 4 else None,
                        "CoolantTemp": data[4] if len(data) >= 5 else None
                    })
            break
        except:
            continue
 
    return pd.DataFrame(rows)
 
 
# ----------------------------------------------------------
# 4. COMPARE EXPECTED VS ACTUAL
# ----------------------------------------------------------
def compare(expected, actual_df):
    results = []
 
    for sig, stats in expected.items():
        if sig not in actual_df.columns:
            actual_min = actual_max = actual_mid = None
        else:
            actual_min = actual_df[sig].min()
            actual_max = actual_df[sig].max()
            actual_mid = (actual_min + actual_max) / 2
 
        res = "PASS" if (actual_min == stats["Min"] and actual_max == stats["Max"]) else "FAIL"
 
        results.append({
            "Signal": sig,
            "Exp Min": stats["Min"],
            "Exp Max": stats["Max"],
            "Exp Mid": stats["Mid"],
            "Act Min": actual_min,
            "Act Max": actual_max,
            "Act Mid": actual_mid,
            "Result": res
        })
 
    return pd.DataFrame(results)
 
 
# ----------------------------------------------------------
# 5. GENERATE HTML REPORT
# ----------------------------------------------------------
def write_html(expected, actual, comparison, out_path):
    html = f"""
<html>
<head>
<style>
    body {{ font-family: Arial; padding: 20px; background: #f3f4f7; }}
    table {{ border-collapse: collapse; width: 90%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
    th {{ background: #333; color: white; }}
    .PASS {{ background: #2ecc71; color: white; }}
    .FAIL {{ background: #e74c3c; color: white; }}
</style>
</head><body>
 
    <h1>Signal Validation Dashboard</h1>
 
    <h2>Expected Values</h2>
    {pd.DataFrame(expected).T.to_html()}
 
    <h2>Actual Sample</h2>
    {actual.head(20).to_html()}
 
    <h2>Comparison</h2>
    {comparison.to_html(index=False, classes=comparison["Result"].tolist())}
 
    </body></html>
    """
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] HTML report saved: {out_path}")

def remote_copy():
    # Remote connection details
    host = "10.210.53.161"
    user = "LC36KOR"
    password = "MSRADARESDST#8"

    # Use forward slashes for Windows path
    remote_path = r"C:/Users/Public/Documents/Vector/CANoe/Projects/CAN_500kBaud_2ch/Logs/SignalReport.blf"
    local_path = r"C:/Users/rbh2cob/Documents/EMS KT/Test_Hackathon/Reports/SignalReport.blf"

    # Connect via SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)

    # SCP transfer
    with SCPClient(ssh.get_transport()) as scp:
        scp.get(remote_path, local_path)  # Pull file from remote

    ssh.close()
    print("✅ BLF file copied to local machine")

 
# ----------------------------------------------------------
# 6. MAIN EXECUTION
# ----------------------------------------------------------
def main():
    remote_copy()
    CAPL1 = r"C:\Users\rbh2cob\Documents\EMS KT\Test_Hackathon\CAPL\MultiSignal.can"
    CAPL2 = r"C:\Users\rbh2cob\Documents\EMS KT\Test_Hackathon\CAPL\MultiSignal_Test.can"
    BLF_FILE = r"C:\Users\rbh2cob\Documents\EMS KT\Test_Hackathon\Reports\SignalReport.blf"    # You run BAT manually → BLF already exists
 
    print("[INFO] Reading expected from CAPL files...")
    es1, tq1, tp1 = parse_capl(CAPL1)
    es2, tq2, tp2 = parse_capl(CAPL2)
 
    es = es1 + es2
    tq = tq1 + tq2
    tp = tp1 + tp2
 
    expected = build_expected_table(es, tq, tp)
 
    print("[INFO] Reading actual values from BLF...")
    df_actual = read_blf(BLF_FILE, msg_id=0x123)
 
    print("[INFO] Comparing...")
    df_compare = compare(expected, df_actual)
 
    print("[INFO] Generating HTML report...")
    write_html(expected, df_actual, df_compare, "SignalDashboard.html")
 
 
if __name__ == "__main__":
    main()
