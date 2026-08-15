"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { ActionButton } from "@/components/action-button";
import {
  createCaseSchema,
  type CreateCaseFormValues,
} from "@/features/cases/schemas/create-case-schema";
import { casesAdapter } from "@/features/cases/services/cases-adapter";

const fieldClassName =
  "min-h-11 w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-4 text-sm text-[color:var(--color-text-strong)] outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)]";

export function CreateCaseForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<CreateCaseFormValues>({
    resolver: zodResolver(createCaseSchema),
    defaultValues: { child_code: "", nickname: "", language: "Thai", notes: "" },
  });

  async function submit(values: CreateCaseFormValues) {
    try {
      const created = await casesAdapter.create(values);
      router.push(`/cases/${encodeURIComponent(created.case_id)}`);
      router.refresh();
    } catch {
      setError("root", {
        message: "The case could not be created. Check the details and try again.",
      });
    }
  }

  return (
    <section className="workspace-panel p-5" aria-labelledby="create-case-heading">
      <h2
        id="create-case-heading"
        className="text-lg font-semibold text-[color:var(--color-text-strong)]"
      >
        Create a de-identified case
      </h2>
      <p className="mt-1 text-sm leading-6 text-[color:var(--color-text-muted)]">
        Use a study or clinic code, not a child&apos;s name or direct identifier. Consent starts as pending.
      </p>
      <form className="mt-5 grid gap-4" onSubmit={handleSubmit(submit)} noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Case code" error={errors.child_code?.message}>
            <input aria-label="Case code" autoComplete="off" className={fieldClassName} {...register("child_code")} />
          </Field>
          <Field label="Nickname" error={errors.nickname?.message} hint="Optional and de-identified">
            <input aria-label="Nickname" autoComplete="off" className={fieldClassName} {...register("nickname")} />
          </Field>
          <Field label="Age in months" error={errors.age_months?.message}>
            <input
              aria-label="Age in months"
              type="number"
              min="0"
              max="240"
              className={fieldClassName}
              {...register("age_months", { valueAsNumber: true })}
            />
          </Field>
          <Field label="Language" error={errors.language?.message}>
            <input aria-label="Language" autoComplete="off" className={fieldClassName} {...register("language")} />
          </Field>
        </div>
        <Field label="Case notes" error={errors.notes?.message} hint="Optional; do not enter direct identifiers">
          <textarea aria-label="Case notes" rows={3} className={`${fieldClassName} py-3`} {...register("notes")} />
        </Field>
        {errors.root?.message ? (
          <p role="alert" className="text-sm text-[color:var(--color-danger-text)]">
            {errors.root.message}
          </p>
        ) : null}
        <div className="flex flex-col gap-3 sm:flex-row">
          <ActionButton type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving case…" : "Save case"}
          </ActionButton>
          <ActionButton type="button" tone="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </ActionButton>
        </div>
      </form>
    </section>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid gap-1 text-sm font-medium text-[color:var(--color-text-strong)]">
      <span>{label}</span>
      {children}
      {error ? (
        <span className="text-xs text-[color:var(--color-danger-text)]">{error}</span>
      ) : hint ? (
        <span className="text-xs font-normal text-[color:var(--color-text-muted)]">{hint}</span>
      ) : null}
    </label>
  );
}
