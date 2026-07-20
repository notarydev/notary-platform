# Notary Python SDK

Local development package for capturing AI decision snapshots.

## Install

```bash
pip install -e packages/notary-sdk-py
```

## Usage

```python
from notary_sdk import RunCapture

capture = RunCapture(secret_key=b"your-secret-key")
capture.capture_llm(prompt="loan app #1234", response="score: 620")
capture.capture_tool(method="POST", url="/score", response={"score": 620})
capture.capture_decision(decision="DENY")
snapshot = capture.finalize()

# Submit to local Notary API
result = snapshot.submit()
```

The SDK is not published to PyPI yet; install from the repo directly.
