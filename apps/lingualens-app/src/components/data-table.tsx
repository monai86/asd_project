type DataTableColumn<T extends Record<string, React.ReactNode>> = {
  key: keyof T;
  header: string;
  align?: "left" | "right";
};

export function DataTable<T extends Record<string, React.ReactNode>>({
  caption,
  columns,
  rows
}: {
  caption: string;
  columns: DataTableColumn<T>[];
  rows: Array<T & { id: string }>;
}) {
  return (
    <div className="overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse" aria-label={caption}>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] text-left">
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  scope="col"
                  className={`px-4 py-3 text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--color-text-subtle)] ${
                    column.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-[color:var(--color-border)] last:border-b-0">
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className={`px-4 py-3 text-sm text-[color:var(--color-text-strong)] ${
                      column.align === "right" ? "text-right" : "text-left"
                    }`}
                  >
                    {row[column.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
