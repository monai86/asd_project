import type { LucideIcon } from "lucide-react";
import {
  AudioLines,
  CalendarDays,
  FileText,
  FolderOpen,
  Settings2,
} from "lucide-react";

export type ShellActive = "Today" | "Cases" | "Session" | "Reports" | "Settings";

export type WorkbenchNavigationItem = {
  href: string;
  label: string;
  active: ShellActive;
  icon: LucideIcon;
};

const SAFE_SESSION_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

export function getWorkbenchNavigation(activeSessionId?: string): readonly WorkbenchNavigationItem[] {
  const normalizedSessionId = activeSessionId?.trim();
  const sessionHref = normalizedSessionId && SAFE_SESSION_ID.test(normalizedSessionId)
    ? `/sessions/${normalizedSessionId}`
    : "/cases?intent=start-session";

  return [
    { href: "/today", label: "Today", active: "Today", icon: CalendarDays },
    { href: "/cases", label: "Cases", active: "Cases", icon: FolderOpen },
    { href: sessionHref, label: "Session", active: "Session", icon: AudioLines },
    { href: "/reports", label: "Reports", active: "Reports", icon: FileText },
    { href: "/settings", label: "Settings", active: "Settings", icon: Settings2 },
  ];
}
