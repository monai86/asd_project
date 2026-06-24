# Therapist App v2 Data Classification Inventory

This inventory defines production handling rules for common Therapist App v2
data classes. It is a launch-readiness control, not a claim that all storage and
deletion flows are fully implemented.

| Data class | Classification | Allowed storage | Retention | Logging rule | Export rule | Deletion rule |
|---|---|---|---|---|---|---|
| Child direct identifiers | Restricted | Encrypted Postgres identity tables; never in object paths, telemetry, or fixtures. | Organization retention policy plus legal hold and applicable consent/privacy obligations. | Never log. Use pseudonymous IDs in operational metadata. | Include only in authorized privacy exports or signed clinical exports where explicitly required. | Subject to deletion review; do not remove audit/sign-off evidence automatically. |
| Pseudonymous case IDs | Confidential | Postgres clinical tables, audit targets, scoped storage metadata. | Same as linked case record. | Allowed in internal audit targets and privacy-safe operational logs when not combined with direct identifiers or clinical content. | Allowed in authorized case exports and operational audit evidence. | Retain in audit/sign-off evidence when required; otherwise follow deletion-review outcome. |
| Transcript text | Restricted | Postgres transcript tables and signed report snapshots when included by clinician action. | Organization retention policy plus legal hold and consent state. | Never log, notify, or send to observability. | Export only after authorization; reviewed CHAT export must identify review/attestation state. | Deletion review required; preserve required audit/sign-off evidence summaries without copying full text into operational tools. |
| Audio files | Restricted | Private encrypted Supabase Storage under server-issued scoped paths. | Media retention policy by organization, country, consent, and legal hold. | Never log audio content, raw filenames, object keys, or signed URLs. | Download only through short-lived signed URLs after FastAPI authorization. | Delete only after retention/deletion review; preserve non-content audit evidence. |
| Report snapshots | Restricted | Postgres signed snapshot fields and/or private export artifact storage. | Retain according to clinical record retention and legal hold. | Never log excerpts or clinical findings. | Signed exports must include signer, timestamp, version, export timestamp, and SHA-256 hash. | Immutable signed snapshots are not silently edited or automatically removed; deletion requires governed review. |
| Audit evidence | Confidential | Append-only Postgres audit tables and backup/PITR systems. | Retain for the longest applicable audit, incident, legal hold, and clinical governance period. | Audit event messages must be generic and contain no clinical content. | Export only to authorized privacy, compliance, or incident-review workflows. | Do not delete automatically for privacy requests; record retained-evidence summaries. |
| Provider metadata | Confidential | Postgres provenance tables and job attempt records. | Match linked transcript/report/job retention and vendor governance requirements. | Provider/model/version/region and input hashes may be logged only as operational metadata; never include payloads, prompts with identifiers, raw transcript text, audio, or storage keys. | Include in authorized provenance exports when needed for audit. | Delete or retain with linked derived record according to deletion review and legal hold. |
| Operational logs | Internal | Approved log/observability provider with retention controls. | `LOG_RETENTION_DAYS` or stricter environment policy. | Route templates, status, latency, correlation IDs, and privacy-safe counters only. No identifiers, transcript text, audio content, storage keys, raw filenames, report excerpts, or clinical content. | Operational exports only for security, compliance, and incident review after safety screening. | Expire per log retention policy unless legal hold or incident preservation applies. |

## Review Requirements

- New product tables, object classes, external providers, or exported artifacts
  must be added to this inventory before production use.
- Data classes marked Restricted require explicit tests or safety validators for
  logs, notifications, audit messages, telemetry, and provider calls.
- Privacy deletion workflows must record what evidence was retained and why,
  without copying restricted clinical content into operational notes.
