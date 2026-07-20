import {
  listBackendCases,
  listBackendReports,
  type BackendCase,
  type BackendReport,
} from "@/lib/workflow";

export type TodayWorkbenchPayload = {
  cases: BackendCase[];
  reports: BackendReport[];
};

export const todayWorkbenchAdapter = {
  async load(signal: AbortSignal): Promise<TodayWorkbenchPayload> {
    const [cases, reports] = await Promise.all([
      listBackendCases({ signal }),
      listBackendReports({ signal }),
    ]);
    if (!Array.isArray(cases) || !Array.isArray(reports)) {
      throw new Error("Today workbench payload did not match the cases/reports contract.");
    }
    return { cases, reports };
  },
};
