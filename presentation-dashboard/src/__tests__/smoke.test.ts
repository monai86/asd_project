import { describe, it, expect } from "vitest";
import projectData from "../data/project_data.json";

describe("Presentation Dashboard Data Smoke Test", () => {
  it("should load presentation database successfully", () => {
    expect(projectData).toBeDefined();
    expect(projectData.model_comparison).toBeDefined();
    expect(projectData.feature_schema).toBeDefined();
    expect(projectData.class_distribution).toBeDefined();
  });

  it("should contain standard logistic regression accuracy details", () => {
    const logReg = projectData.model_comparison.find(
      (m: any) => m.model === "LogReg" && m.task === "binary"
    );
    expect(logReg).toBeDefined();
    if (logReg) {
      expect(logReg.accuracy).toBeGreaterThan(0.8);
      expect(logReg.roc_auc).toBeGreaterThan(0.9);
    }
  });
});
