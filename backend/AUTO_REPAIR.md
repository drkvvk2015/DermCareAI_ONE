# Guardrailed automatic repair

DermCareAI includes a **proposal-only** CI repair layer.

## Safety boundary

The repair layer may classify failures and prepare a minimal repair proposal, but it
does not directly edit, commit, merge, deploy, or silently alter clinical logic.

Clinical/AI safety paths are explicitly protected:

- `backend/dermatology/`
- `backend/clinical.py`
- `backend/evaluation.py`
- `backend/model_registry.py`
- `backend/ai_governance.py`

A future GitHub automation can use this module to create a **draft PR only**, followed
by the normal CI gates and human review. Automatic changes to protected clinical paths
remain disabled by design.
