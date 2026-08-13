"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import type { SettingsSection } from "@/features/settings/services/settings-access";

const SECTION_LABELS: Readonly<Record<SettingsSection, string>> = {
  account: "Account",
  organization: "Organization",
  accessibility: "Accessibility & Display",
  notifications: "Notifications",
  privacy: "Privacy & Security",
  export: "Export",
  help: "Help",
  team: "Team",
  invitations: "Invitations",
  audit: "Audit",
  privacy_operations: "Privacy Operations",
  integration_status: "Integration Status",
};

const ADMIN_SECTIONS = new Set<SettingsSection>([
  "team",
  "invitations",
  "audit",
  "privacy_operations",
  "integration_status",
]);

type SettingsNavigationProps = {
  sections: readonly SettingsSection[];
  selected: SettingsSection;
  onSelect: (section: SettingsSection) => void;
  mobileIndexOpen?: boolean;
  onOpenMobileIndex?: () => void;
};

export function SettingsNavigation({
  sections,
  selected,
  onSelect,
  mobileIndexOpen = true,
  onOpenMobileIndex,
}: SettingsNavigationProps) {
  const sharedSections = sections.filter((section) => !ADMIN_SECTIONS.has(section));
  const adminSections = sections.filter((section) => ADMIN_SECTIONS.has(section));

  return (
    <nav aria-label="Settings categories mobile">
      {!mobileIndexOpen ? (
        <button
          type="button"
          className="flex min-h-11 w-full items-center gap-2 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] px-3 text-left text-sm font-semibold text-ink md:hidden"
          onClick={onOpenMobileIndex}
        >
          <ChevronLeft size={17} aria-hidden="true" />
          All settings categories
        </button>
      ) : null}
      <div className={`${mobileIndexOpen ? "block" : "hidden md:block"} sticky top-24 rounded-[var(--radius-card)] border border-line bg-[color:var(--color-surface-reading)] p-2`}>
        <div className="md:hidden">
          <p className="px-3 pb-3 pt-1 text-sm leading-6 text-slate-600">Choose one category to open its settings page.</p>
        </div>
          <SettingsNavGroup label="Workspace settings" sections={sharedSections} selected={selected} onSelect={onSelect} />
          {adminSections.length > 0 ? (
            <div className="mt-3 border-t border-line pt-3">
              <SettingsNavGroup label="Organization administration" sections={adminSections} selected={selected} onSelect={onSelect} />
            </div>
          ) : null}
      </div>
    </nav>
  );
}

function SettingsNavGroup({
  label,
  onSelect,
  sections,
  selected,
}: Pick<SettingsNavigationProps, "sections" | "selected" | "onSelect"> & { label: string }) {
  return (
    <div>
      <p className="px-3 pb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <ul className="grid gap-1">
        {sections.map((section) => {
          const isSelected = section === selected;
          return (
            <li key={section}>
              <a
                href={`/settings?section=${section}`}
                aria-current={isSelected ? "page" : undefined}
                className={`flex min-h-11 items-center rounded-md border-l-2 px-3 py-2 text-sm font-medium transition ${
                  isSelected
                    ? "border-clinical bg-cyan-50 text-cyan-900"
                    : "border-transparent text-slate-700 hover:bg-slate-50 hover:text-ink"
                }`}
                onClick={(event) => {
                  event.preventDefault();
                  onSelect(section);
                }}
              >
                <span className="flex-1">{SECTION_LABELS[section]}</span>
                <ChevronRight size={16} aria-hidden="true" className="text-slate-400 md:hidden" />
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function settingsSectionLabel(section: SettingsSection): string {
  return SECTION_LABELS[section];
}
