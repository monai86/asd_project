import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ClinicalPdfReport } from "@/features/reports/components/clinical-pdf-report";

const SAMPLE_DATA = {
  childName: "น้องออโต้ (Nong Auto)",
  age: "3y 4m",
  evaluator: "นักอรรถบำบัด สมศรี",
  date: "2026-08-12",
  receptiveSummary: "เข้าใจคำสั่ง 2 ขั้นตอนได้ดี สามารถชี้วัตถุตามคำสั่งได้",
  expressiveSummary: "พูดเป็นประโยค 3-4 คำได้ ใช้คำเชื่อมอย่างง่ายได้",
  pragmaticsSummary: "สบตาได้ตามวัย ตอบสนองต่อชื่อดี",
  talkBankScore: 0.82,
  hash: "a1b2c3d4e5f67890abcdef1234567890abcdef12",
  recommendations: ["ฝึกการเล่าเรื่องตามลำดับเหตุการณ์", "เพิ่มกิจกรรมเล่นสมมติ"],
};

describe("ClinicalPdfReport", () => {
  it("renders report title in both languages", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByText(/Speech-Language Assessment Report/i)).toBeInTheDocument();
    expect(screen.getByText(/แบบรายงานผล/i)).toBeInTheDocument();
  });

  it("renders Print / Download PDF button", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByRole("button", { name: /Print \/ Download PDF/i })).toBeInTheDocument();
  });

  it("renders child demographics", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByText(/น้องออโต้/i)).toBeInTheDocument();
    expect(screen.getByText(/3y 4m/i)).toBeInTheDocument();
  });

  it("renders assessment sections", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByText(/การเข้าใจภาษา/i)).toBeInTheDocument();
    expect(screen.getByText(/การแสดงออกทางภาษา/i)).toBeInTheDocument();
    expect(screen.getByText(/การสื่อสารตามบริบทสังคม/i)).toBeInTheDocument();
  });

  it("renders SHA-256 hash verification", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByText(/SHA-256/i)).toBeInTheDocument();
  });

  it("renders recommendations list", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    expect(screen.getByText(/ฝึกการเล่าเรื่อง/i)).toBeInTheDocument();
  });

  it("renders evaluator signature block", () => {
    render(<ClinicalPdfReport data={SAMPLE_DATA} />);
    // Evaluator name appears in demographics AND signature block
    const evaluatorElements = screen.getAllByText(/นักอรรถบำบัด สมศรี/i);
    expect(evaluatorElements.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Speech-Language Pathologist/i)).toBeInTheDocument();
  });
});
