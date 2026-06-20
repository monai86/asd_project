export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <header className="mb-6 border-b border-line pb-5">
      <p className="mb-3 inline-flex rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-safety">
        Clinical decision-support prototype
      </p>
      <h1 className="text-2xl font-semibold tracking-normal text-ink sm:text-3xl">{title}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
    </header>
  );
}
