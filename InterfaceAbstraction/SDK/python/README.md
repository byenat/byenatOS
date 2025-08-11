# ByenatOS Python SDK (minimal)

Quick Start:

```bash
pip install -r requirements.txt
export BYENATOS_API_BASE=http://localhost:8080
python - <<'PY'
from InterfaceAbstraction.SDK.python.byenatos_sdk import ByenatOS
sdk = ByenatOS()
print(sdk.get_personalized_prompt(user_id="user_123", current_request="plan my day"))
PY
```