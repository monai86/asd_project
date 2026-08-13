import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

vi.mock("@/features/cases/hooks/use-cases-workspace", () => ({
  useCasesWorkspace: (caseId?: string) => caseId
    ? { status: "detail", detail: { caseItem: { case_id: caseId } } }
    : { status: "list", list: { cases: [] } },
}));

vi.mock("@/features/cases/components/case-list", () => ({
  CaseList: () => <section data-testid="case-list-feature" />,
}));

vi.mock("@/features/cases/components/case-detail", () => ({
  CaseDetail: () => <section data-testid="case-detail-feature" />,
}));

import { CasesWorkspaceClient } from "@/components/cases-workspace-client";

test("dispatches the case collection to the feature-owned list", () => {
  render(<CasesWorkspaceClient />);
  expect(screen.getByTestId("case-list-feature")).toBeInTheDocument();
});

test("dispatches a selected case to the feature-owned detail", () => {
  render(<CasesWorkspaceClient caseId="case-001" />);
  expect(screen.getByTestId("case-detail-feature")).toBeInTheDocument();
});
