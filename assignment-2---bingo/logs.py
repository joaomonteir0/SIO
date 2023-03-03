import time
import hashlib
from utils import *

# ADD TO LOGS AND TRACK LOGS
def request_log(log, start, end):
  return log[start:end]

def new_log(log, text, private_key):
    entry = {
        "sequence": len(log) + 1,
        "timestamp": time.time(),
    }
    entry["hash"] = hashlib.sha256(str(entry['sequence']).encode("utf-8")).hexdigest()
    entry["text"] = text
    entry["signature"] = base64.b64encode(sign_msg(private_key, text)).decode("utf-8")

    log.append(tuple(entry.values()))

def verify_log_integrity(log, public_key):
    for entry in log:
        sequence, timestamp, entry_hash, text, signature = entry
        prev_hash = hashlib.sha256(str(sequence).encode("utf-8")).hexdigest()
        if prev_hash != entry_hash:
            return False

        if validate_msg_integrity({"signature": signature, "text": text}, "text", public_key)["status"] != "success":
            return False
    return True 