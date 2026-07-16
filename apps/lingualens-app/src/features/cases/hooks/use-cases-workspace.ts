"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { casesAdapter } from "@/features/cases/services/cases-adapter";
import { useMockAccessSession } from "@/lib/use-mock-access-session";
import {
  assignCaseCareTeamMember,
  getBackendCaseTimeline,
  listBackendCaseGoals,
  listCaseCareTeamAssignments,
  listOrganizationMemberships,
  updateBackendCase,
  withdrawBackendCaseConsent,
  type BackendCase,
  type BackendGoal,
  type BackendTimelineEvent,
  type CareTeamAssignment,
  type OrganizationMembership,
} from "@/lib/workflow";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

type CasesResource =
  | { kind: "list"; cases: BackendCase[] }
  | { kind: "detail"; caseItem: BackendCase; timeline: BackendTimelineEvent[]; goals: BackendGoal[] };

export type CaseListViewModel = {
  cases: BackendCase[];
};

export type CaseConsentViewModel = {
  localConsent: string;
  consentSigner: string;
  setConsentSigner: Dispatch<SetStateAction<string>>;
  consentChecked: boolean;
  setConsentChecked: Dispatch<SetStateAction<boolean>>;
  consentDate: string;
  setConsentDate: Dispatch<SetStateAction<string>>;
  consentNotes: string;
  setConsentNotes: Dispatch<SetStateAction<string>>;
  consentBusy: boolean;
  consentMsg: string;
  grantConsent: () => Promise<void>;
  withdrawConsent: () => Promise<void>;
};

export type CaseCareTeamViewModel = {
  activeAssignments: CareTeamAssignment[];
  primaryAssignment?: CareTeamAssignment;
  availableMemberships: OrganizationMembership[];
  loading: boolean;
  busy: boolean;
  message: string;
  selectedUserId: string;
  setSelectedUserId: Dispatch<SetStateAction<string>>;
  selectedRole: string;
  setSelectedRole: Dispatch<SetStateAction<string>>;
  makePrimary: boolean;
  setMakePrimary: Dispatch<SetStateAction<boolean>>;
  refreshAssignments: () => Promise<void>;
  assign: () => Promise<void>;
  promotePrimary: (userId: string) => Promise<void>;
  deactivateAssignment: (assignment: CareTeamAssignment) => Promise<void>;
};

export type CaseDetailViewModel = {
  caseItem: BackendCase;
  timeline: BackendTimelineEvent[];
  goals: BackendGoal[];
  consent: CaseConsentViewModel;
  careTeam: CaseCareTeamViewModel;
};

export type CasesWorkspaceViewModel =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "error" }
  | { status: "list"; list: CaseListViewModel }
  | { status: "detail"; detail: CaseDetailViewModel };

async function loadCasesResource(identity: string, signal: AbortSignal): Promise<CasesResource> {
  if (identity === "cases:list") {
    return { kind: "list", cases: await casesAdapter.list(signal) };
  }
  const caseId = identity.slice("cases:detail:".length);
  const [caseItem, timeline, goals] = await Promise.all([
    casesAdapter.get(caseId, signal),
    getBackendCaseTimeline(caseId, { signal }),
    listBackendCaseGoals(caseId, { signal }),
  ]);
  return { kind: "detail", caseItem, timeline, goals };
}

function clinicianLabel(userId: string) {
  if (userId === "therapist-demo") return "Demo Therapist";
  return userId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function useCasesWorkspace(caseId?: string): CasesWorkspaceViewModel {
  const resource = useRemoteResource(
    caseId ? `cases:detail:${caseId}` : "cases:list",
    loadCasesResource,
  );
  const session = useMockAccessSession();
  const data = resource.status === "success" || resource.status === "stale" ? resource.data : undefined;
  const currentCase = data?.kind === "detail" ? data.caseItem : undefined;
  const currentCaseId = currentCase?.case_id;
  const currentConsentStatus = currentCase?.consent_status;
  const primaryTherapistUserId = currentCase?.primary_therapist_user_id;
  const currentCaseIdRef = useRef(currentCaseId);
  currentCaseIdRef.current = currentCaseId;

  const [localConsent, setLocalConsent] = useState("pending");
  const [consentSigner, setConsentSigner] = useState("Parent");
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentDate, setConsentDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [consentNotes, setConsentNotes] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentMsg, setConsentMsg] = useState("");

  useEffect(() => {
    setLocalConsent("pending");
    setConsentSigner("Parent");
    setConsentChecked(false);
    setConsentDate(new Date().toISOString().slice(0, 10));
    setConsentNotes("");
    setConsentBusy(false);
    setConsentMsg("");
  }, [currentCaseId]);

  useEffect(() => {
    setLocalConsent(currentConsentStatus ?? "pending");
  }, [currentCaseId, currentConsentStatus]);

  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [assignments, setAssignments] = useState<CareTeamAssignment[]>([]);
  const [careTeamLoading, setCareTeamLoading] = useState(false);
  const [careTeamBusy, setCareTeamBusy] = useState(false);
  const [careTeamMessage, setCareTeamMessage] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedRole, setSelectedRole] = useState("therapist");
  const [makePrimary, setMakePrimary] = useState(false);

  useEffect(() => {
    if (!currentCaseId) {
      setMemberships([]);
      setAssignments([]);
      setCareTeamLoading(false);
      return;
    }
    let cancelled = false;
    setCareTeamLoading(true);
    setCareTeamBusy(false);
    setCareTeamMessage("");
    setSelectedRole("therapist");
    setMakePrimary(false);
    void (async () => {
      try {
        const [loadedAssignments, loadedMemberships] = await Promise.all([
          listCaseCareTeamAssignments(currentCaseId),
          listOrganizationMemberships(),
        ]);
        if (cancelled) return;
        setAssignments(loadedAssignments);
        const activeMemberships = loadedMemberships.filter((member) => member.active);
        setMemberships(activeMemberships);
        const firstAssignable = activeMemberships.find((member) => member.user_id !== primaryTherapistUserId);
        setSelectedUserId(firstAssignable?.user_id ?? activeMemberships[0]?.user_id ?? "");
      } catch {
        if (!cancelled) setCareTeamMessage("Care-team management requires the local backend admin flow.");
      } finally {
        if (!cancelled) setCareTeamLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [currentCaseId, primaryTherapistUserId, session?.organizationId]);

  const refreshAssignments = useCallback(async () => {
    if (!currentCase) return;
    const targetCaseId = currentCase.case_id;
    const loadedAssignments = await listCaseCareTeamAssignments(targetCaseId);
    if (currentCaseIdRef.current === targetCaseId) {
      setAssignments(loadedAssignments);
    }
  }, [currentCase]);

  const activeAssignments = useMemo(() => assignments.filter((item) => item.active), [assignments]);
  const primaryAssignment = useMemo(() => activeAssignments.find((item) => item.is_primary), [activeAssignments]);
  const availableMemberships = useMemo(
    () => memberships.filter((member) => !activeAssignments.some((item) => item.user_id === member.user_id)),
    [activeAssignments, memberships],
  );

  async function grantConsent() {
    if (!currentCase || !consentChecked) return;
    const targetCaseId = currentCase.case_id;
    setConsentBusy(true);
    setConsentMsg("");
    try {
      await updateBackendCase(currentCase.case_id, {
        consent_status: "granted",
        notes: `${currentCase.notes || ""}\nConsent verified on ${consentDate} by ${consentSigner}. Notes: ${consentNotes}`.trim(),
      });
      if (currentCaseIdRef.current === targetCaseId) {
        setLocalConsent("granted");
        setConsentMsg("Caregiver consent has been successfully verified and saved.");
      }
    } catch {
      if (currentCaseIdRef.current === targetCaseId) {
        setConsentMsg("Failed to verify consent on the backend. Please retry.");
      }
    } finally {
      if (currentCaseIdRef.current === targetCaseId) setConsentBusy(false);
    }
  }

  async function withdrawConsent() {
    if (!currentCase) return;
    const targetCaseId = currentCase.case_id;
    setConsentBusy(true);
    setConsentMsg("");
    try {
      await withdrawBackendCaseConsent(currentCase.case_id, "Therapist request", true);
      if (currentCaseIdRef.current === targetCaseId) {
        setLocalConsent("withdrawn");
        setConsentMsg("Consent has been successfully withdrawn. Case details redacted.");
      }
    } catch {
      if (currentCaseIdRef.current === targetCaseId) {
        setConsentMsg("Failed to withdraw consent. Please try again.");
      }
    } finally {
      if (currentCaseIdRef.current === targetCaseId) setConsentBusy(false);
    }
  }

  async function assign() {
    if (!currentCase || !selectedUserId) return;
    const targetCaseId = currentCase.case_id;
    setCareTeamBusy(true);
    setCareTeamMessage("");
    try {
      await assignCaseCareTeamMember(currentCase.case_id, {
        user_id: selectedUserId,
        role: selectedRole,
        active: true,
        is_primary: makePrimary,
      });
      await refreshAssignments();
      if (currentCaseIdRef.current !== targetCaseId) return;
      const promotedLabel = memberships.find((member) => member.user_id === selectedUserId)?.display_name ?? clinicianLabel(selectedUserId);
      setCareTeamMessage(makePrimary ? `Primary therapist reassigned to ${promotedLabel}.` : `Care-team assignment updated for ${promotedLabel}.`);
      setMakePrimary(false);
    } catch (error) {
      if (currentCaseIdRef.current === targetCaseId) {
        setCareTeamMessage(error instanceof Error ? error.message : "Could not update the care team.");
      }
    } finally {
      if (currentCaseIdRef.current === targetCaseId) setCareTeamBusy(false);
    }
  }

  async function promotePrimary(userId: string) {
    if (!currentCase) return;
    const targetCaseId = currentCase.case_id;
    const existing = activeAssignments.find((item) => item.user_id === userId);
    if (!existing) return;
    setCareTeamBusy(true);
    setCareTeamMessage("");
    try {
      await assignCaseCareTeamMember(currentCase.case_id, {
        user_id: existing.user_id,
        role: existing.role,
        active: true,
        is_primary: true,
      });
      await refreshAssignments();
      if (currentCaseIdRef.current === targetCaseId) {
        setCareTeamMessage(`Primary therapist reassigned to ${clinicianLabel(userId)}.`);
      }
    } catch (error) {
      if (currentCaseIdRef.current === targetCaseId) {
        setCareTeamMessage(error instanceof Error ? error.message : "Could not reassign the primary therapist.");
      }
    } finally {
      if (currentCaseIdRef.current === targetCaseId) setCareTeamBusy(false);
    }
  }

  async function deactivateAssignment(assignment: CareTeamAssignment) {
    if (!currentCase) return;
    const targetCaseId = currentCase.case_id;
    setCareTeamBusy(true);
    setCareTeamMessage("");
    try {
      await assignCaseCareTeamMember(currentCase.case_id, {
        user_id: assignment.user_id,
        role: assignment.role,
        active: false,
        is_primary: false,
      });
      await refreshAssignments();
      if (currentCaseIdRef.current === targetCaseId) {
        setCareTeamMessage(assignment.is_primary
          ? `Primary therapist assignment removed for ${clinicianLabel(assignment.user_id)}. Report sign-off stays blocked until reassigned.`
          : `Care-team assignment removed for ${clinicianLabel(assignment.user_id)}.`);
      }
    } catch (error) {
      if (currentCaseIdRef.current === targetCaseId) {
        setCareTeamMessage(error instanceof Error ? error.message : "Could not deactivate the care-team assignment.");
      }
    } finally {
      if (currentCaseIdRef.current === targetCaseId) setCareTeamBusy(false);
    }
  }

  if (resource.status === "loading" || resource.status === "idle") return { status: "loading" };
  if (resource.status === "error") return { status: caseId ? "error" : "unavailable" };
  if (!data) return { status: "loading" };
  if (data.kind === "list") return { status: "list", list: { cases: data.cases } };

  return {
    status: "detail",
    detail: {
      caseItem: data.caseItem,
      timeline: data.timeline,
      goals: data.goals,
      consent: {
        localConsent,
        consentSigner,
        setConsentSigner,
        consentChecked,
        setConsentChecked,
        consentDate,
        setConsentDate,
        consentNotes,
        setConsentNotes,
        consentBusy,
        consentMsg,
        grantConsent,
        withdrawConsent,
      },
      careTeam: {
        activeAssignments,
        primaryAssignment,
        availableMemberships,
        loading: careTeamLoading,
        busy: careTeamBusy,
        message: careTeamMessage,
        selectedUserId,
        setSelectedUserId,
        selectedRole,
        setSelectedRole,
        makePrimary,
        setMakePrimary,
        refreshAssignments,
        assign,
        promotePrimary,
        deactivateAssignment,
      },
    },
  };
}
