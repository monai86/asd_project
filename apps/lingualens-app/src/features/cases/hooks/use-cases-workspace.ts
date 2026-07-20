"use client";

import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { casesAdapter } from "@/features/cases/services/cases-adapter";
import {
  getBackendCaseTimeline,
  listBackendCaseGoals,
  updateBackendCase,
  withdrawBackendCaseConsent,
  type BackendCase,
  type BackendGoal,
  type BackendTimelineEvent,
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

export type CaseDetailViewModel = {
  caseItem: BackendCase;
  timeline: BackendTimelineEvent[];
  goals: BackendGoal[];
  consent: CaseConsentViewModel;
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

export function useCasesWorkspace(caseId?: string): CasesWorkspaceViewModel {
  const resource = useRemoteResource(
    caseId ? `cases:detail:${caseId}` : "cases:list",
    loadCasesResource,
  );
  const data = resource.status === "success" || resource.status === "stale" ? resource.data : undefined;
  const currentCase = data?.kind === "detail" ? data.caseItem : undefined;
  const currentCaseId = currentCase?.case_id;
  const currentConsentStatus = currentCase?.consent_status;
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
    },
  };
}
