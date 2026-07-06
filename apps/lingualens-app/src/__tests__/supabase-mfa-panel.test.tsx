import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SupabaseMfaPanel } from "@/components/supabase-mfa-panel";
import { routerRefresh } from "@/__tests__/setup";

const listFactors = vi.fn();
const enroll = vi.fn();
const challengeAndVerify = vi.fn();
const getSession = vi.fn();

vi.mock("@/lib/supabase-browser-client", () => ({
  getSupabaseBrowserClient: () => ({
    auth: {
      getSession,
      mfa: {
        listFactors,
        enroll,
        challengeAndVerify,
      },
    },
  }),
}));

describe("SupabaseMfaPanel failure states", () => {
  beforeEach(() => {
    listFactors.mockReset();
    enroll.mockReset();
    challengeAndVerify.mockReset();
    getSession.mockReset();
    routerRefresh.mockClear();
  });

  it("shows a clear alert when MFA factors cannot be loaded", async () => {
    listFactors.mockResolvedValue({
      data: null,
      error: { message: "MFA factor lookup failed." },
    });

    render(<SupabaseMfaPanel email="clinician@clinic.example" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("MFA factor lookup failed.");
    expect(screen.getByRole("button", { name: "Start TOTP enrollment" })).toBeInTheDocument();
  });

  it("shows an enrollment error without unlocking workspace access", async () => {
    listFactors.mockResolvedValue({
      data: {
        all: [],
        totp: [],
        phone: [],
        webauthn: [],
      },
      error: null,
    });
    enroll.mockResolvedValue({
      data: null,
      error: { message: "Enrollment service unavailable." },
    });

    render(<SupabaseMfaPanel email="clinician@clinic.example" />);

    const enrollButton = await screen.findByRole("button", { name: "Start TOTP enrollment" });
    await waitFor(() => expect(enrollButton).toBeEnabled());
    fireEvent.click(enrollButton);

    expect(await screen.findByRole("alert")).toHaveTextContent("Enrollment service unavailable.");
    expect(screen.queryByText("MFA verified. Refreshing workspace access.")).not.toBeInTheDocument();
  });

  it("shows a verification error and does not refresh the workspace", async () => {
    listFactors.mockResolvedValue({
      data: {
        all: [{
          id: "factor_totp_001",
          factor_type: "totp",
          status: "verified",
          friendly_name: "LinguaLens Authenticator",
        }],
        totp: [{
          id: "factor_totp_001",
          factor_type: "totp",
          status: "verified",
          friendly_name: "LinguaLens Authenticator",
        }],
        phone: [],
        webauthn: [],
      },
      error: null,
    });
    challengeAndVerify.mockResolvedValue({
      data: null,
      error: { message: "Invalid authentication code." },
    });

    render(<SupabaseMfaPanel email="clinician@clinic.example" />);

    fireEvent.change(await screen.findByLabelText("Authenticator code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify TOTP and continue" }));

    await waitFor(() => {
      expect(challengeAndVerify).toHaveBeenCalledWith({
        factorId: "factor_totp_001",
        code: "123456",
      });
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid authentication code.");
    expect(routerRefresh).not.toHaveBeenCalled();
  });
});
