from pathlib import Path
from drf_omtir_flight_recorder.receipt import write_trust_receipt

wal_path = Path(r"C:\Users\vikra\Documents\GitHub\drf-omtir-flight-recorder\wal\truefoundry-real-mcp-v0.2.0.jsonl")
receipt_path = Path(r"C:\Users\vikra\Documents\GitHub\drf-omtir-flight-recorder\receipts\truefoundry-real-mcp-v0.2.0-trust-receipt.md")

write_trust_receipt(wal_path, receipt_path, root=Path(r"C:\Users\vikra\Documents\GitHub\drf-omtir-flight-recorder"))

print(f"Trust Receipt regenerated at: {receipt_path}")
