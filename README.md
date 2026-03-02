# Asset Tracking ITAM App (MVP Scaffold)

A runnable IT asset management web app focused on IT-only lifecycle workflows.

## Features implemented
- Dashboard with inventory KPIs.
- Asset CRUD-lite (create/list/detail).
- Checkout wizard with policy acknowledgement/signature capture.
- Check-in wizard with damaged-return path (`in_repair`).
- Users, locations, reports, integrations, and audit log views.
- Core validation rules:
  - unique serial and asset tag,
  - normalized serial numbers,
  - cannot checkout retired/lost/in_repair assets,
  - due date cannot be in the past.
- API endpoints for asset creation/list and checkout.
- SQLite persistence and audit event capture.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: `http://127.0.0.1:8000`

## Tests
```bash
pytest -q
```

## Notes
- Integrations page currently provides connection status and simulated sync action. This is the extension point for Kandji/ABM jobs.
- Designed as a single-org app now; can evolve to multi-tenant by adding `org_id` scoping throughout.
