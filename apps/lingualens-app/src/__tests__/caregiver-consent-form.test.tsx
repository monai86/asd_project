import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CaregiverConsentForm } from "@/components/caregiver-consent-form";

function renderForm(overrides: Partial<Parameters<typeof CaregiverConsentForm>[0]> = {}) {
  const onSubmit = vi.fn((event: { preventDefault: () => void }) => event.preventDefault());
  render(
    <CaregiverConsentForm
      busy={false}
      checked={false}
      onCheckedChange={vi.fn()}
      signer="Parent"
      onSignerChange={vi.fn()}
      consentDate="2026-07-17"
      onConsentDateChange={vi.fn()}
      notes=""
      onNotesChange={vi.fn()}
      onSubmit={onSubmit}
      submitLabel="Verify and Grant Consent"
      idPrefix="test"
      {...overrides}
    />,
  );
  return { onSubmit };
}

describe("CaregiverConsentForm", () => {
  it("renders one bilingual confirmation statement and the full field set", () => {
    renderForm();

    expect(screen.getByRole("checkbox", { name: /I verify that written or verbal caregiver consent has been obtained\./ })).toBeInTheDocument();
    expect(screen.getByText(/ข้าพเจ้ายืนยันว่าได้รับการลงนามยินยอมจากผู้ปกครอง/)).toBeInTheDocument();
    expect(screen.getByLabelText("Signer relationship")).toBeInTheDocument();
    expect(screen.getByLabelText("Consent date")).toBeInTheDocument();
    expect(screen.getByLabelText("Verification notes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verify and Grant Consent" })).toBeDisabled();
  });

  it("explains why submission is blocked and links it to the submit button", () => {
    renderForm({ submitBlockedReason: "Check the confirmation box to verify caregiver consent was obtained.", reasonId: "test-grant-consent-reason" });

    const submitButton = screen.getByRole("button", { name: "Verify and Grant Consent" });
    expect(submitButton).toHaveAttribute("aria-describedby", "test-grant-consent-reason");
    expect(screen.getByText("Check the confirmation box to verify caregiver consent was obtained.")).toBeInTheDocument();
  });

  it("enables submission once the confirmation box is checked", () => {
    let checked = false;
    const onCheckedChange = (value: boolean) => {
      checked = value;
    };
    const { rerender } = render(
      <CaregiverConsentForm
        busy={false}
        checked={checked}
        onCheckedChange={onCheckedChange}
        signer="Parent"
        onSignerChange={vi.fn()}
        consentDate="2026-07-17"
        onConsentDateChange={vi.fn()}
        notes=""
        onNotesChange={vi.fn()}
        onSubmit={vi.fn()}
        submitLabel="Verify and Grant Consent"
        idPrefix="test"
      />,
    );
    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    rerender(
      <CaregiverConsentForm
        busy={false}
        checked={checked}
        onCheckedChange={onCheckedChange}
        signer="Parent"
        onSignerChange={vi.fn()}
        consentDate="2026-07-17"
        onConsentDateChange={vi.fn()}
        notes=""
        onNotesChange={vi.fn()}
        onSubmit={vi.fn()}
        submitLabel="Verify and Grant Consent"
        idPrefix="test"
      />,
    );
    expect(screen.getByRole("button", { name: "Verify and Grant Consent" })).toBeEnabled();
  });

  it("submits the verification through the host handler", () => {
    const { onSubmit } = renderForm({ checked: true });
    fireEvent.click(screen.getByRole("button", { name: "Verify and Grant Consent" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
