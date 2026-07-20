"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

import {
  assignCaseCareTeamMember,
  listBackendCases,
  listCaseCareTeamAssignments,
  type BackendCase,
  type CareTeamAssignment,
  type OrganizationMembership,
} from "@/lib/workflow";

export function CareTeamAdministration({
  initialCaseId,
  memberships,
}: {
  initialCaseId: string | null;
  memberships: OrganizationMembership[];
}) {
  const [cases, setCases] = useState<BackendCase[]>([]);
  const [caseId, setCaseId] = useState(initialCaseId ?? "");
  const [assignments, setAssignments] = useState<CareTeamAssignment[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedRole, setSelectedRole] = useState("therapist");
  const [makePrimary, setMakePrimary] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void listBackendCases()
      .then((loadedCases) => {
        if (cancelled) return;
        if (!Array.isArray(loadedCases)) throw new Error("Malformed case list payload.");
        setCases(loadedCases);
        setCaseId((current) => current || initialCaseId || loadedCases[0]?.case_id || "");
      })
      .catch(() => {
        if (!cancelled) setMessage("Could not load cases for care-team administration.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [initialCaseId]);

  const refreshAssignments = useCallback(async (targetCaseId = caseId) => {
    if (!targetCaseId) {
      setAssignments([]);
      return;
    }
    const loaded = await listCaseCareTeamAssignments(targetCaseId);
    setAssignments(loaded);
  }, [caseId]);

  useEffect(() => {
    let cancelled = false;
    if (!caseId) return;
    setLoading(true);
    void listCaseCareTeamAssignments(caseId)
      .then((loaded) => {
        if (!cancelled) setAssignments(loaded);
      })
      .catch(() => {
        if (!cancelled) setMessage("Care-team assignments require an authorized organization-admin session.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [caseId]);

  const activeAssignments = assignments.filter((assignment) => assignment.active);
  const activeMemberships = memberships.filter((member) => member.active);
  const assignableMemberships = activeMemberships.filter(
    (member) => !activeAssignments.some((assignment) => assignment.user_id === member.user_id),
  );
  const effectiveSelectedUserId = assignableMemberships.some((member) => member.user_id === selectedUserId)
    ? selectedUserId
    : assignableMemberships[0]?.user_id ?? "";

  async function updateAssignment(payload: { user_id: string; role: string; active: boolean; is_primary: boolean }) {
    if (!caseId) return;
    setBusy(true);
    setMessage("");
    try {
      await assignCaseCareTeamMember(caseId, payload);
      await refreshAssignments(caseId);
      setMakePrimary(false);
      setMessage("Care-team assignment updated. The backend audit trail records this organization action.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update the care-team assignment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="clinical-card rounded-md p-4" aria-labelledby="care-team-admin-title">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-700">Admin only</p>
          <h2 id="care-team-admin-title" className="mt-2 text-lg font-semibold text-ink">Care-team administration</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-700">
            Select a case to manage active assignments and primary sign-off ownership. Every request remains backend-authorized.
          </p>
        </div>
        <label className="grid w-full min-w-0 gap-1 text-sm font-medium text-ink lg:w-64">
          Case
          <select className="min-h-11 w-full min-w-0 max-w-full rounded-md border border-line bg-field px-3" value={caseId} onChange={(event) => setCaseId(event.target.value)}>
            {cases.map((caseItem) => <option key={caseItem.case_id} value={caseItem.case_id}>{caseItem.nickname ?? caseItem.child_code ?? caseItem.case_id}</option>)}
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-3">
        {loading ? <p className="text-sm text-slate-600">Loading care-team assignments...</p> : null}
        {!loading && activeAssignments.length === 0 ? <p className="text-sm text-slate-600">No active assignments for this case.</p> : null}
        {activeAssignments.map((assignment) => (
          <div key={assignment.assignment_id} className="flex flex-col gap-3 rounded-md border border-line bg-field p-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-ink">{membershipLabel(memberships, assignment.user_id)}</p>
              <p className="text-sm text-slate-600">{assignment.role}{assignment.is_primary ? " · primary therapist" : ""}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {!assignment.is_primary ? <button type="button" className="min-h-11 rounded-md border border-line px-3 text-sm font-semibold" disabled={busy} onClick={() => void updateAssignment({ user_id: assignment.user_id, role: assignment.role, active: true, is_primary: true })}>Make primary therapist</button> : null}
              <button type="button" className="min-h-11 rounded-md border border-line px-3 text-sm font-semibold" disabled={busy} onClick={() => void updateAssignment({ user_id: assignment.user_id, role: assignment.role, active: false, is_primary: false })}>Remove assignment</button>
            </div>
          </div>
        ))}
      </div>

      <form className="mt-4 grid min-w-0 gap-3 rounded-md border border-line bg-field p-3 lg:grid-cols-[minmax(0,1fr)_180px_auto_auto] lg:items-end" onSubmit={(event) => { event.preventDefault(); void updateAssignment({ user_id: effectiveSelectedUserId, role: selectedRole, active: true, is_primary: makePrimary }); }}>
        <label className="grid gap-1 text-sm font-medium text-ink">Organization member<select className="min-h-11 rounded-md border border-line bg-white px-3" value={effectiveSelectedUserId} onChange={(event) => setSelectedUserId(event.target.value)} disabled={!assignableMemberships.length || busy}>{assignableMemberships.length ? assignableMemberships.map((member) => <option key={member.user_id} value={member.user_id}>{member.display_name} · {member.role}</option>) : <option value="">No additional active memberships</option>}</select></label>
        <label className="grid gap-1 text-sm font-medium text-ink">Care-team role<select className="min-h-11 rounded-md border border-line bg-white px-3" value={selectedRole} onChange={(event) => setSelectedRole(event.target.value)} disabled={busy}><option value="therapist">Therapist</option><option value="clinical_supervisor">Clinical supervisor</option><option value="org_admin">Org admin</option></select></label>
        <label className="flex min-h-11 items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={makePrimary} onChange={(event) => setMakePrimary(event.target.checked)} disabled={busy} />Make primary</label>
        <div className="flex gap-2"><button type="submit" className="min-h-11 rounded-md bg-clinical px-4 text-sm font-semibold text-white disabled:opacity-50" disabled={busy || !effectiveSelectedUserId || !caseId}>Assign</button><button type="button" className="min-h-11 rounded-md border border-line px-3" aria-label="Refresh care-team assignments" disabled={busy || !caseId} onClick={() => void refreshAssignments()}><RefreshCw size={16} aria-hidden="true" /></button></div>
      </form>
      {message ? <p aria-live="polite" className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 px-3 py-2 text-sm text-cyan-950">{message}</p> : null}
    </section>
  );
}

function membershipLabel(memberships: OrganizationMembership[], userId: string) {
  return memberships.find((member) => member.user_id === userId)?.display_name ?? userId;
}
