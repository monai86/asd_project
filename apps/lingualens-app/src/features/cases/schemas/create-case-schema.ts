import { z } from "zod";

export const createCaseSchema = z.object({
  child_code: z.string().trim().min(1, "Case code is required.").max(64),
  nickname: z.string().trim().max(120).optional(),
  age_months: z.number({ invalid_type_error: "Age in months is required." }).int().min(0).max(240),
  language: z.string().trim().min(1, "Language is required.").max(64),
  notes: z.string().trim().max(2000).optional(),
});

export type CreateCaseFormValues = z.infer<typeof createCaseSchema>;
