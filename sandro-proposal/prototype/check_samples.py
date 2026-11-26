"""Run the synthetic sample set through the running server and compare to expected.json.

Usage (server must be running):  .venv/bin/python check_samples.py [base_url]
"""
import json
import sys
import urllib.request
import uuid
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
SAMPLES = Path(__file__).parent / "samples"
expected = json.loads((SAMPLES / "expected.json").read_text())

# Same request the "Use the synthetic sample set" button sends.
boundary = uuid.uuid4().hex
body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"applicant\"\r\n\r\n{expected['applicant']}\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"use_samples\"\r\n\r\n1\r\n--{boundary}--\r\n").encode()
req = urllib.request.Request(f"{BASE}/check", data=body,
                             headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
got = json.load(urllib.request.urlopen(req))

status = {i["id"]: i["status"] for i in got["items"]}
bad = [(k, v, status.get(k)) for k, v in expected["status"].items() if status.get(k) != v]
if sorted(got["unrecognised"]) != sorted(expected["unrecognised"]):
    bad.append(("unrecognised", expected["unrecognised"], got["unrecognised"]))

print(f"mode={got['mode']}")
print(got["text"])
if bad:
    print("\nFAIL:")
    for k, want, have in bad:
        print(f"  {k}: expected {want}, got {have}")
    sys.exit(1)
print("\nPASS: gap list matches expected.json")
