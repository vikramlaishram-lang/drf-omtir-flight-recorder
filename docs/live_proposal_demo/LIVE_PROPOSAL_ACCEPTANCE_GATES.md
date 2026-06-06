\# Live Proposal Demo Acceptance Gates v0.2



Required command:



drf-omtir live-proposal-demo



Required WAL fields:



LIVE\_MODEL\_OUTPUT

raw\_model\_output\_sha256

parsed\_proposal

drf\_decision

tool\_execution\_boundary



Acceptance commands:



python -m pip install -e .

drf-omtir --help

drf-omtir live-proposal-demo

drf-omtir verify wal/live-proposal-demo.jsonl

Select-String -Path wal/live-proposal-demo.jsonl -Pattern "LIVE\_MODEL\_OUTPUT"

Select-String -Path wal/live-proposal-demo.jsonl -Pattern "raw\_model\_output\_sha256"

Select-String -Path wal/live-proposal-demo.jsonl -Pattern "parsed\_proposal"

python -m pytest



The command must fail closed if TrueFoundry credentials are missing or model output is malformed after retry.

