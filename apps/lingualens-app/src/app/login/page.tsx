import { WorkflowVisual } from "@/components/app-shell";
import { RuntimeLoginPanelClient } from "@/components/runtime-login-panel-client";

export default function LoginPage() {
  return (
    <main className="min-h-dvh bg-[color:var(--color-page-bg)] px-4 py-6 text-[color:var(--color-text-strong)] sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100dvh-3rem)] w-full max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(22rem,26rem)]">
        <section className="min-w-0">
          <p className="mb-4 inline-flex rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 py-1.5 text-xs font-semibold text-[color:var(--color-accent-strong)]">
            Clinical transcript workbench
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-[color:var(--color-text-strong)] sm:text-5xl">
            LinguaLens
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[color:var(--color-text-muted)]">
            Review child language samples, verify transcript evidence, and prepare therapist-signed progress reports from one controlled workspace.
          </p>
          <div className="mt-8 grid gap-3 text-sm text-[color:var(--color-text-muted)] sm:grid-cols-3">
            <div className="control-strip px-4 py-3">
              <p className="font-semibold text-[color:var(--color-text-strong)]">Transcript first</p>
              <p className="mt-1">Line-level review before feature extraction.</p>
            </div>
            <div className="control-strip px-4 py-3">
              <p className="font-semibold text-[color:var(--color-text-strong)]">Human sign-off</p>
              <p className="mt-1">Reports remain therapist-owned.</p>
            </div>
            <div className="control-strip px-4 py-3">
              <p className="font-semibold text-[color:var(--color-text-strong)]">Private runtime</p>
              <p className="mt-1">Access follows the configured auth policy.</p>
            </div>
          </div>
          <div className="mt-8">
            <WorkflowVisual />
          </div>
        </section>
        <RuntimeLoginPanelClient />
      </div>
    </main>
  );
}
