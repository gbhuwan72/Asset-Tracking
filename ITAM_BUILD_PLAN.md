# IT Asset Management (ITAM) Build-Ready Plan

## 1) Product Requirements Document (PRD)

### 1.1 Product vision and goals
Build a reliable, audit-first ITAM platform for IT-only assets across the full lifecycle:
**procure → enroll → assign → track → service → retire**.

Primary outcomes:
1. One trustworthy record per physical device.
2. Fast, accountable check-in/check-out with user acknowledgement.
3. Reliable sync with **Kandji** and **Apple Business Manager (ABM)**.
4. Complete immutable audit trail for security, finance, and compliance stakeholders.

### 1.2 Personas and jobs-to-be-done

#### A) IT Admin / IT Manager (power user)
- JTBD:
  - “When I receive or deploy hardware, I need accurate inventory and status so I can plan and report.”
  - “When auditors ask for a trail, I need immutable records and exports immediately.”
  - “When MDM/ABM data differs from local records, I need a clear reconciliation workflow.”

#### B) IT Technician / Helpdesk (operational user)
- JTBD:
  - “When handing out devices, I need a fast checkout flow that captures signatures and condition.”
  - “When devices return, I need quick check-in, accessory validation, and damage notes/photos.”
  - “When doing stock counts, I need scan-first workflows on mobile.”

#### C) Employee (requester/assignee)
- JTBD:
  - “When I receive a device, I need clear policy and what I’m responsible for.”
  - “When I return or transfer equipment, I need a clear confirmation and receipt.”

#### D) Finance / Audit (read-only)
- JTBD:
  - “When doing financial or compliance review, I need clean exports and lifecycle status history.”
  - “When warranty/depreciation deadlines approach, I need scheduled reports.”

### 1.3 Scope definition

#### MVP (must-have to launch)
- Core asset repository (IT assets only).
- Mandatory identifiers: serial number, asset tag; optional ABM and Kandji IDs.
- Lifecycle states: `in_stock`, `pending_enrollment`, `assigned`, `checked_out`, `in_repair`, `lost`, `retired`.
- Check-out/check-in flows with:
  - identity confirmation,
  - optional due date,
  - condition notes,
  - optional photo,
  - accessories list,
  - acknowledgement/signature,
  - policy text capture.
- Bulk check-out and transfer between users.
- Offboarding return flow.
- Integrations:
  - Kandji import/sync,
  - ABM import/sync,
  - reconciliation queue/dashboard.
- Immutable audit log for all create/update/state transitions.
- Reports: asset by user, overdue assets, inventory by location, enrollment gaps, warranty expiry, lifecycle summary.
- CSV/Excel export and scheduled email reports.
- RBAC with least privilege and SSO login.

#### V1 (next wave)
- Scheduled checkouts/reservations with approval.
- Accessory-level serial tracking and partial returns workflow improvements.
- Slack notifications (check-out receipts, overdue reminders, integration failures).
- Barcode/QR scan optimizations and camera scanner UX refinements.
- Depreciation placeholders with configurable formulas and finance metadata.

#### V2 (advanced)
- Offline-capable mobile PWA mode with sync conflict UI.
- Policy versioning and legal-hold retention flags.
- Multi-org tenant partitioning + tenant-level admin.
- Predictive lifecycle insights (replacement forecasting).

#### Explicit out-of-scope (for MVP)
- Non-IT asset classes (furniture, facilities, fleet).
- Full procurement/ERP replacement.
- Ticketing suite replacement.
- Endpoint management actions (locking/wiping) from this app.

### 1.4 Core user stories with acceptance criteria

1. **Create and maintain asset record**
- As IT admin, I can create an asset with required identifiers and lifecycle state.
- Acceptance:
  - Serial number required and unique (case-insensitive).
  - Asset tag required and unique per org.
  - Cannot set `retired` asset back to `checked_out` without admin override.

2. **Quick checkout**
- As technician, I can check out an asset to an employee in under 60 seconds.
- Acceptance:
  - Employee identity must be selected and confirmed.
  - Policy text must be displayed and acknowledgement captured.
  - Receipt generated and sent (email; Slack optional if configured).
  - Asset state transitions to `checked_out`; assignment record created.

3. **Check-in / return**
- As technician, I can process return and capture condition/accessories.
- Acceptance:
  - Returned items list must support accessory-level status.
  - Damage flag requires notes; photo optional.
  - New state set to `in_stock` or `in_repair` based on condition.

4. **Bulk checkout**
- As admin, I can assign multiple assets in one transaction.
- Acceptance:
  - Up to configurable limit (e.g., 100 assets/transaction).
  - Per-asset result recorded (success/failure reason).
  - Transaction audit entry includes all affected asset IDs.

5. **Offboarding**
- As IT admin, I can start offboarding for an employee and track unreturned assets.
- Acceptance:
  - System lists all active assignments.
  - Return due date can be set globally or per asset.
  - Overdue reminders auto-scheduled; escalations supported.

6. **Integration reconciliation**
- As admin, I can resolve mismatches between app, Kandji, and ABM.
- Acceptance:
  - Dashboard shows unmatched and conflicting records.
  - Suggested matches by serial + model + last seen proximity.
  - Resolution action requires reason and is audited.

7. **Audit export**
- As auditor, I can export immutable activity logs by date range.
- Acceptance:
  - Exports include actor, action, timestamp, before/after snapshot hash.
  - Deleted records represented as tombstone events, not physical deletion.

### 1.5 Roles and permissions model

- **Org Admin**: full access; manage settings, integrations, roles, overrides, retention policy.
- **IT Admin**: manage assets, users, assignments, check-in/out, repairs, reports.
- **IT Technician**: operate check-in/out, scan, basic updates, no integration configuration.
- **Employee Self-Service**: view assigned assets, acknowledge checkout/return, submit requests.
- **Finance/Audit Read-Only**: reports/export/audit log read-only, no write actions.
- **Integration Service Account**: API-only scoped token for inbound sync jobs.

Permission granularity (minimum):
- `asset.read`, `asset.write`, `asset.retire`, `asset.override_state`
- `assignment.create`, `assignment.transfer`, `assignment.close`
- `repair.create`, `repair.update`
- `report.read`, `report.export`
- `audit.read`
- `integration.read`, `integration.write`, `integration.sync`
- `admin.roles.manage`, `admin.settings.manage`

### 1.6 Audit/compliance requirements
- Immutable append-only event log.
- Each event contains cryptographic hash chain (`prev_hash`, `event_hash`) for tamper evidence.
- UTC timestamp, actor, source IP/user agent (where applicable), object type/id, action, before/after JSON.
- Soft-delete only for business entities; no hard delete outside legal purge process.
- Retention defaults:
  - Audit logs: 7 years.
  - Transaction records (checkout/check-in): 7 years.
  - Integration job logs/errors: 18 months.
- Export formats: CSV and JSONL.
- Signed export metadata: generated time, requester, filters, record count.

---

## 2) Data model & domain design

### 2.1 Entity model (core fields)

#### Asset
- `id` (UUID)
- `asset_tag` (string, required, unique)
- `serial_number` (string, required, unique normalized)
- `device_type` (enum: laptop/desktop/tablet/phone/accessory-other)
- `status` (enum lifecycle)
- `model`, `manufacturer`, `color`, `spec_json`
- `purchase_order_id` (FK)
- `vendor_id` (FK)
- `location_id` (FK current)
- `assigned_user_id` (FK nullable denormalized current holder)
- `abm_device_id` (string nullable unique)
- `kandji_device_id` (string nullable unique)
- `created_at`, `updated_at`, `retired_at`

#### Device (logical management snapshot)
- `id` (UUID)
- `asset_id` (FK unique)
- `platform` (macOS/iOS/iPadOS)
- `os_version`
- `enrollment_status` (enum)
- `last_seen_at`
- `mdm_status`
- `abm_status`
- `supervised` (bool)
- `source_last_payload_json`

#### User
- `id` (UUID)
- `employee_id` (string unique nullable)
- `email` (string required unique)
- `display_name`
- `department`, `cost_center`
- `manager_user_id` (FK nullable)
- `status` (active/inactive/offboarding)
- `role` (rbac role)

#### Assignment
- `id` (UUID)
- `asset_id` (FK)
- `user_id` (FK)
- `assigned_at`
- `expected_return_at` (nullable)
- `returned_at` (nullable)
- `reason` (new hire/replacement/loaner/etc.)
- `state` (active/closed/overdue/transferred)

#### CheckoutTransaction
- `id` (UUID)
- `type` (checkout/checkin/transfer/offboarding/bulk)
- `initiated_by_user_id` (FK)
- `subject_user_id` (FK nullable)
- `location_id` (FK)
- `policy_version`
- `acknowledged_at`
- `signature_blob_ref` (nullable)
- `photo_refs` (array nullable)
- `condition_notes`
- `due_date` (nullable)
- `status` (completed/partial/failed/overridden)
- `override_reason` (nullable)

#### Location
- `id`, `name`, `code`, `address_json`, `timezone`, `active`

#### Vendor
- `id`, `name`, `contact_email`, `support_phone`, `sla_notes`

#### PurchaseOrder
- `id`, `po_number` (unique), `vendor_id`, `order_date`, `received_date`, `currency`, `total_amount`, `status`

#### Warranty
- `id`, `asset_id`, `provider`, `start_date`, `end_date`, `terms_json`, `status`

#### RepairTicket
- `id`, `asset_id`, `opened_by_user_id`, `vendor_id`, `issue_type`, `description`, `opened_at`, `closed_at`, `repair_status`, `cost_amount`

#### Accessory
- `id`, `parent_asset_id` (FK), `name`, `serial_number` (nullable unique), `quantity`, `is_required_on_return`, `status`

#### ImportJob
- `id`, `source` (kandji/abm/csv), `started_at`, `finished_at`, `status`, `records_received`, `records_created`, `records_updated`, `records_failed`, `error_summary_json`

#### IntegrationConnection
- `id`, `provider` (kandji/abm), `auth_type`, `encrypted_credentials_ref`, `status`, `last_success_at`, `last_error_at`, `rate_limit_state_json`

#### AuditLog
- `id`, `event_ts`, `actor_type`, `actor_id`, `action`, `object_type`, `object_id`, `before_json`, `after_json`, `reason`, `request_id`, `ip`, `user_agent`, `prev_hash`, `event_hash`

### 2.2 Relationships
- `Asset 1—1 Device`
- `Asset 1—N Assignment`
- `Asset 1—N Warranty` (if renewals/extensions tracked)
- `Asset 1—N RepairTicket`
- `Asset 1—N Accessory`
- `Vendor 1—N PurchaseOrder`; `PurchaseOrder 1—N Asset`
- `Location 1—N Asset`; `Location 1—N CheckoutTransaction`
- `User 1—N Assignment`; `User 1—N CheckoutTransaction`

### 2.3 Lifecycle states and transitions
Allowed states: `in_stock`, `pending_enrollment`, `assigned`, `checked_out`, `in_repair`, `lost`, `retired`.

Key transition rules:
- `in_stock -> pending_enrollment | checked_out | assigned | in_repair | retired`
- `pending_enrollment -> in_stock | assigned | checked_out | in_repair`
- `checked_out -> in_stock | in_repair | lost | retired` (retired requires return/override)
- `assigned -> checked_out | in_stock | in_repair | lost | retired`
- `in_repair -> in_stock | retired | lost`
- `lost -> in_stock | retired` (admin override with reason)
- `retired` is terminal (except admin override with explicit reason + audit)

### 2.4 Validation rules
- Serial numbers normalized (trim/uppercase) and unique per org.
- Asset tag unique and immutable after first assignment unless admin override.
- Cannot checkout `retired` or `lost` assets.
- Cannot checkin asset without active assignment/checkout context unless admin override.
- Due date cannot be in the past at checkout creation.
- Transfer requires current holder and receiving user.
- Accessory marked `is_required_on_return=true` must be acknowledged on check-in (returned/missing/damaged).
- ABM/Kandji IDs unique when present.

---

## 3) Integration design (Kandji + ABM)

### 3.1 Integration goals
- Ingest and keep current device metadata: serial, model, OS, last seen, enrollment status, assigned user (if available).
- Reconcile duplicates and split-brain records across internal app, Kandji, ABM.
- Provide deterministic source-of-truth ownership by field.

### 3.2 Source-of-truth strategy (field authority)
- **App authoritative**: asset tag, purchase/finance metadata, internal location, checkout transactions, policy acknowledgements.
- **Kandji authoritative**: device management state (`last_seen_at`, `os_version`, `mdm_status`, compliance posture, assigned user hint).
- **ABM authoritative**: device procurement/enrollment eligibility, ABM device identity, ABM assignment status.
- **Derived by reconciliation rules**: canonical `enrollment_status` and mapping confidence.

### 3.3 Sync mechanism
- Polling baseline:
  - Kandji every 15 min delta sync (last-updated cursor).
  - ABM every 6 hours plus nightly full consistency check.
- Webhooks (if provider supports events reliably): near-real-time updates for enrollment/assignment changes.
- Retry/backoff:
  - Exponential backoff with jitter (1m, 5m, 15m, 60m; max 6 attempts).
  - Dead-letter queue for persistent failures.
- Rate-limit handling:
  - Respect provider headers, adaptive worker concurrency, token bucket per provider/org.

### 3.4 Field mapping

#### Kandji → our app
- `device_id` → `Asset.kandji_device_id`
- `serial_number` → `Asset.serial_number` (match key)
- `device_name` → `Device.source_last_payload_json.device_name`
- `model` → `Asset.model`
- `platform` → `Device.platform`
- `os_version` → `Device.os_version`
- `last_check_in`/`last_seen` → `Device.last_seen_at`
- `enrollment_status` → `Device.enrollment_status`
- `user.email` (if present) → candidate link to `User.email`

#### ABM → our app
- `abm_device_id` → `Asset.abm_device_id`
- `serial_number` → `Asset.serial_number` (match key)
- `model`/`part_number` → `Asset.model` / metadata
- `added_to_abm_at` → `Device.source_last_payload_json.abm_added_at`
- `mdm_server_assignment` → `Device.abm_status` (assigned/unassigned)
- `order_number` (if available) → `PurchaseOrder.po_number` candidate match

### 3.5 Duplicate detection and reconciliation
Matching order:
1. Strong key exact match: serial number.
2. Provider IDs (`abm_device_id`, `kandji_device_id`) if already linked.
3. Fuzzy candidate: model + purchase date window + location + last seen proximity.

Resolution actions:
- Auto-merge if strong key exact and no conflicting immutable fields.
- Flag “needs review” for any conflicting serial/identifier or multi-candidate match.
- Manual merge requires admin role and reason code.

### 3.6 Reconciliation dashboard concept
Widgets:
- **Unmatched ABM devices** (in ABM, not in app)
- **Unmatched Kandji devices** (in Kandji, not in app)
- **ABM but not Kandji** (enrollment gap)
- **Kandji but not ABM** (procurement/enrollment anomaly)
- **Field conflicts** (e.g., model mismatch)
- **Sync health timeline** (jobs, latency, errors)

Table actions:
- Link to existing asset
- Create new asset from source payload
- Ignore with reason + expiration
- Force refresh record

### 3.7 Error handling + alerting
- Classify errors: auth, rate-limit, schema drift, provider outage, data conflict.
- Alerting thresholds:
  - Any auth failure immediate alert.
  - >5% failed records in a job triggers warning.
  - No successful sync >2 intervals triggers critical.
- Delivery channels: in-app alert center + email + optional Slack webhook.
- Include runbook links in alerts.

---

## 4) Check-in / check-out flow design

### 4.1 Quick checkout
1. Scan/search asset.
2. Validate asset eligibility (not retired/lost/in repair).
3. Confirm employee identity (email + directory lookup).
4. Add due date (optional), accessories, condition baseline.
5. Display policy text + capture acknowledgement/signature.
6. Submit transaction; update state to `checked_out`; create assignment.
7. Issue receipt (email/Slack).

### 4.2 Scheduled checkout
- Create future assignment with reservation status.
- At pickup, convert reservation to active checkout with acknowledgement/signature.
- Auto-expire no-show after configurable grace period.

### 4.3 Bulk checkout
- Upload/select asset list + target user or mapping file.
- Preflight validations for each asset.
- Execute as transaction batch with per-item results.
- Partial success allowed, all failures explained.

### 4.4 Return / check-in
1. Find active assignment.
2. Scan returned assets/accessories.
3. Capture condition notes and optional photos.
4. Mark each accessory returned/missing/damaged.
5. Decide post-return state: `in_stock` or `in_repair`.
6. Close assignment and generate receipt.

### 4.5 Partial returns (accessories)
- Support asset returned with missing accessories.
- Keep assignment closed but generate follow-up obligation item.
- Optionally create chargeback note for finance workflow.

### 4.6 Transfers between users
- Validate current assignment holder.
- Capture both source and destination acknowledgement.
- New assignment created; prior assignment closed with transfer reason.

### 4.7 Offboarding
- Trigger by user status = offboarding or manual action.
- Bundle all active assets into offboarding case.
- Set due dates, reminders, escalation recipients.
- If unreturned by deadline: mark risk state and optional `lost` transition via admin.

### 4.8 Required capture controls
- Identity confirmation: required.
- Due date: optional but recommended for loaners.
- Condition notes: required on check-in if not “good”.
- Photo: optional.
- Accessories: required selection and status.
- Signature/acknowledgement: required for checkout and transfer.
- Policy text: versioned and stored with transaction.

### 4.9 Receipt templates (generic)

#### Email receipt (checkout)
Subject: `Asset Checkout Confirmation - {{asset_tag}}`
Body:
- Employee: {{name}} ({{email}})
- Asset: {{model}} / Serial {{serial}} / Tag {{asset_tag}}
- Accessories: {{accessory_list}}
- Checkout time: {{timestamp}}
- Due date: {{due_date_or_none}}
- Policy acknowledged: v{{policy_version}}
- Processed by: {{it_staff}}

#### Slack receipt (optional)
`✅ Asset checked out: {{asset_tag}} to {{employee_email}} | Due: {{due_date_or_none}} | By: {{it_staff}}`

### 4.10 Edge cases
- Lost/stolen: capture incident date, notes, police report ref (optional), set state `lost`, notify security/admin.
- Damaged return: mandatory damage notes; optional repair ticket auto-create.
- No-show returns: auto reminders + escalation path.
- Offline mode (V2): local queue with signed drafts + conflict resolution on reconnect.
- Admin override: any policy/state bypass requires reason; high-visibility audit entry.

---

## 5) UX outline

### 5.1 Navigation map
- Dashboard
- Assets
  - Asset List
  - Asset Detail
- Check-out / Check-in
  - Scan Screen
  - Checkout Wizard
  - Check-in Wizard
- Users
- Locations
- Reports
- Integrations
- Audit Log
- Admin Settings

### 5.2 Key screens

#### Dashboard
- KPI cards: total assets, checked out, overdue, in repair, lost, enrollment gaps.
- “Needs attention” queue: overdue returns, integration failures, unresolved conflicts.

#### Asset List
- Columns: asset tag, serial, model, state, assigned user, location, last seen, warranty end, ABM linked, Kandji linked.
- Filters: state, location, model, assigned user, warranty window, enrollment status, source mismatch, last seen range.
- Bulk actions: checkout, transfer, retire, export.

#### Asset Detail
- Header: identifiers + status + quick actions.
- Tabs: overview, assignment history, repairs, warranties, integration data, audit trail.

#### Scan Screen
- Camera scan (QR/barcode) + manual entry fallback.
- Instant asset status badge and eligibility warning.

#### Checkout Wizard
- Stepper: asset → user → accessories → policy/signature → confirm.
- Real-time validation and warning banners.

#### Check-in Wizard
- Stepper: assignment lookup → returned items → condition/photo → disposition → confirm.

#### Users
- User profile, assigned assets, offboarding status, history.

#### Integrations
- Connection health, credentials status, last sync, run now, job history.

#### Audit Log
- Filterable immutable event viewer with export.

### 5.3 Minimal mobile-first check-in/out UI spec
- Single-column layout, large touch targets.
- Search/scan persistent at top.
- Progressive disclosure (hide advanced fields under “More options”).
- Sticky bottom CTA (Next/Confirm).
- Low-latency design target: <300ms per step transition.
- Accessible contrast, keyboard-friendly fallback for scanners.

---

## 6) Reporting & audit

### 6.1 Required reports
1. Assets by user
2. Overdue assets
3. Inventory by location
4. Enrollment gaps:
   - ABM in, Kandji missing
   - Kandji in, app missing
5. Warranty expiry (30/60/90 days)
6. Lifecycle summary (counts by state + transitions over time)
7. Depreciation placeholder (base fields exported for finance tooling)

### 6.2 Export formats & scheduling
- On-demand: CSV, XLSX, JSONL.
- Scheduled: daily/weekly/monthly with timezone-aware execution.
- Delivery: email attachments + secure download link; optional Slack file/link.
- Export policy:
  - Respect RBAC and row-level constraints.
  - Log each export in AuditLog with filters and row count.

### 6.3 Audit log schema examples

Example 1: Checkout completed
```json
{
  "event_ts": "2026-01-15T18:21:33Z",
  "actor_id": "user_123",
  "action": "checkout.completed",
  "object_type": "asset",
  "object_id": "asset_456",
  "before_json": {"status":"in_stock"},
  "after_json": {"status":"checked_out","assigned_user_id":"user_987"},
  "reason": "new_hire",
  "prev_hash": "...",
  "event_hash": "..."
}
```

Example 2: Admin override
```json
{
  "event_ts": "2026-01-16T11:03:02Z",
  "actor_id": "admin_001",
  "action": "asset.state_override",
  "object_type": "asset",
  "object_id": "asset_456",
  "before_json": {"status":"retired"},
  "after_json": {"status":"in_repair"},
  "reason": "data_fix_after_intake_error",
  "prev_hash": "...",
  "event_hash": "..."
}
```

---

## 7) Security & privacy

### 7.1 Authentication and access
- Prefer SSO via SAML/OIDC (Okta, Entra, Google Workspace).
- MFA enforced by IdP policy.
- Just-in-time user provisioning optional; SCIM later.
- RBAC enforced server-side on every API operation.

### 7.2 Data protection
- TLS 1.2+ in transit.
- Encryption at rest (AES-256 managed keys).
- Secrets in managed vault (rotated, scoped, audited).
- Token scopes minimized for Kandji/ABM integration credentials.

### 7.3 Privacy and PII minimization
- Store only required employee attributes: email, name, employee ID (optional), department/cost center.
- Avoid storing sensitive HR details.
- PII export redaction options for finance/audit audiences.
- Data retention and deletion policy documented and enforceable.

### 7.4 Single-org now, multi-tenant later
- MVP deployment can be single-org but design schema with `org_id` on all domain tables.
- All unique indexes should include `org_id` for future partitioning.
- Integration tokens scoped per `org_id`.

---

## 8) Delivery blueprint (implementation readiness)

### 8.1 Suggested architecture
- Frontend: web admin + responsive check-in/out module.
- Backend: REST/GraphQL API, job queue workers, scheduler.
- DB: PostgreSQL (transactional + JSONB for source payload snapshots).
- Object storage: signatures/photos.
- Event bus (optional): for audit stream + async notifications.

### 8.2 API surface (initial)
- `POST /assets`, `GET /assets`, `GET /assets/{id}`, `PATCH /assets/{id}`
- `POST /checkout-transactions/checkout`
- `POST /checkout-transactions/checkin`
- `POST /checkout-transactions/transfer`
- `POST /offboarding/cases`
- `GET /reports/*`
- `POST /integrations/{provider}/sync`
- `GET /reconciliation/items`, `POST /reconciliation/{id}/resolve`
- `GET /audit-logs`

### 8.3 Non-functional requirements (MVP targets)
- Availability: 99.9% monthly.
- p95 API latency: <400ms for core reads, <800ms for transactional writes.
- Import throughput: 10k devices/hour baseline.
- Idempotent integration ingest (safe retries).
- Disaster recovery: daily backups, PITR enabled.

### 8.4 Launch KPIs
- Inventory accuracy >98% by serial match.
- Checkout completion time median <90 seconds.
- Reconciliation unresolved queue <2% of managed assets.
- Overdue asset rate reduced by 30% within first quarter.

