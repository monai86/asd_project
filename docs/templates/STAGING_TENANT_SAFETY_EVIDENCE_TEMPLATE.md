# Tenant-Safety Promotion Gate Evidence

- Date:
- Commit:
- Staging API:
- Staging therapist app:
- Supabase project ref:
- Operator:
- Reviewer:
- Result:

## Preconditions

- [ ] Staging Supabase project exists in `ap-southeast-1`.
- [ ] `LINGUALENS_AUTH_MODE=supabase` is active on staging API.
- [ ] Public signup is off.
- [ ] Invitation-only onboarding is enabled.
- [ ] Claims match `docs/SUPABASE_AUTH_CONTRACT.md`.
- [ ] `org_a` and `org_b` exist in staging.
- [ ] At least one seeded case exists in each organization.

## Scenario Results

| Scenario | Result | Evidence reference | Correlation/request IDs | Notes |
|---|---|---|---|---|
| Cross-org clinical read denial |  |  |  |  |
| Cross-org clinical write denial |  |  |  |  |
| Assigned therapist access only |  |  |  |  |
| Clinical supervisor org-wide access |  |  |  |  |
| Org admin assignment-safe default |  |  |  |  |
| Backend tenant-isolation smoke |  |  |  |  |
| Explicit clinical grant through care-team assignment |  |  |  |  |
| Platform operator routine denial |  |  |  |  |
| Scoped break-glass case access |  |  |  |  |
| Break-glass expiry fail-closed |  |  |  |  |
| Membership revocation fail-closed |  |  |  |  |

## Evidence Inventory

- Screenshots:
- API snippets:
- Audit event snippets:
- Seed data references:

## Exceptions Or Failures

- None / describe:

## Approval

- Engineering/Product:
- Legal/Privacy:
