"use client";

export const MOCK_ACCESS_SESSION_KEY = "lingualens.mock-access-session.v1";
export const MOCK_ACCESS_SESSION_EVENT = "lingualens:mock-access-session-changed";

export type MockRole = "therapist" | "clinical_supervisor" | "org_admin";

export type MockAccessSession = {
  role: MockRole;
  organizationId: string;
  aal: "aal1" | "aal2";
};

export type MockOrganizationOption = {
  organizationId: string;
  label: string;
  membershipMode: "single" | "multi";
};

export const MOCK_ORGANIZATION_OPTIONS: Record<MockRole, MockOrganizationOption[]> = {
  therapist: [
    { organizationId: "pilot_org_001", label: "Pilot Speech Clinic", membershipMode: "single" },
  ],
  clinical_supervisor: [
    { organizationId: "pilot_org_001", label: "Pilot Speech Clinic", membershipMode: "multi" },
    { organizationId: "pilot_org_002", label: "North Review Clinic", membershipMode: "multi" },
  ],
  org_admin: [
    { organizationId: "pilot_org_001", label: "Pilot Speech Clinic", membershipMode: "multi" },
    { organizationId: "pilot_org_ops", label: "Operations Training Clinic", membershipMode: "multi" },
  ],
};

export function loadMockAccessSession(): MockAccessSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(MOCK_ACCESS_SESSION_KEY);
    if (!raw) {
      const defaultSession: MockAccessSession = {
        role: "therapist",
        organizationId: "pilot_org_001",
        aal: "aal2",
      };
      window.sessionStorage.setItem(MOCK_ACCESS_SESSION_KEY, JSON.stringify(defaultSession));
      return defaultSession;
    }
    const parsed = JSON.parse(raw) as Partial<MockAccessSession>;
    if (
      typeof parsed.role === "string" &&
      typeof parsed.organizationId === "string" &&
      parsed.organizationId.trim() &&
      (parsed.aal === "aal1" || parsed.aal === "aal2")
    ) {
      return { role: parsed.role as MockRole, organizationId: parsed.organizationId, aal: parsed.aal };
    }
  } catch {
    return null;
  }
  return null;
}

export function saveMockAccessSession(session: MockAccessSession): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(MOCK_ACCESS_SESSION_KEY, JSON.stringify(session));
  window.dispatchEvent(new CustomEvent(MOCK_ACCESS_SESSION_EVENT, { detail: session }));
}

export function updateMockAccessSessionAal(aal: "aal1" | "aal2"): void {
  const current = loadMockAccessSession();
  if (!current) return;
  saveMockAccessSession({ ...current, aal });
}

export function updateMockAccessSessionOrganizationId(organizationId: string): void {
  const current = loadMockAccessSession();
  if (!current) return;
  saveMockAccessSession({ ...current, organizationId });
}

export function getMockOrganizationOptions(role: MockRole): MockOrganizationOption[] {
  return MOCK_ORGANIZATION_OPTIONS[role];
}

export function resolveOrganizationLabel(organizationId: string): string {
  const allOptions = Object.values(MOCK_ORGANIZATION_OPTIONS).flat();
  return allOptions.find((option) => option.organizationId === organizationId)?.label ?? organizationId;
}
