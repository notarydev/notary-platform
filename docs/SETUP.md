# Notary Platform — Setup

## Deployed Demo Setup

```bash
git clone https://github.com/notarydev/notary-platform.git
cd notary-platform
make install
source .venv/bin/activate
export NOTARY_API_URL=https://api.getnotary.ai
export NOTARY_API_TOKEN=<your-demo-token>
```

## Local Development Setup

```bash
git clone https://github.com/notarydev/notary-platform.git
cd notary-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e packages/notary-sdk-py
make run
export NOTARY_API_URL=http://localhost:8000
export NOTARY_API_TOKEN=<local-token-if-auth-enabled>
```

### SDK Snippet (runnable)

```python
from notary_sdk import RunCapture

capture = RunCapture(
    secret_key=b"demo-secret",
    api_url="http://localhost:8000",
    api_token="",
)

capture.capture_human_action(source_record_ref="APP-1234", domain="Lending")
capture.capture_llm(prompt="Loan application", response="Need credit score", model="demo-model", temperature=0.0, seed=12345)
capture.capture_tool(method="POST", url="https://demo.notary.local/credit-bureau", response={"score": 650}, status=200)
capture.capture_decision(decision="DENY", expected_correct_behavior="APPROVE")

snapshot = capture.finalize(agent_version="loan-agent@candidate", policy_version="credit-policy-v1")
result = snapshot.submit(source_system_id="sys:lending", source_record_ref="APP-1234", agent_id="agent:lending", business_function="Personal loan underwriting")
print(f"Created Verification Record: {result.get('id')}")
```

See also [README.md](../README.md) for the full API reference.
