import {
  CheckCircle,
  Clock,
  Info,
  SignOut,
  Warning,
  WarningOctagon,
  XCircle,
  HourglassMedium,
  type Icon,
} from "@phosphor-icons/react";
import type { AttendanceStatus, Severity } from "@/lib/types";
import { cn } from "./cn";

interface Tone {
  label: string;
  icon: Icon;
  className: string;
}

export const STATUS_TONE: Record<AttendanceStatus, Tone> = {
  present: { label: "Present", icon: CheckCircle, className: "bg-good-soft text-good" },
  late: { label: "Late", icon: Clock, className: "bg-warn-soft text-warn" },
  left: { label: "Left", icon: SignOut, className: "bg-neutral-soft text-neutral" },
  absent: { label: "Absent", icon: XCircle, className: "bg-bad-soft text-bad" },
  pending: { label: "Not seen yet", icon: HourglassMedium, className: "bg-neutral-soft text-muted" },
};

export const SEVERITY_TONE: Record<Severity, Tone> = {
  info: { label: "Info", icon: Info, className: "bg-accent-soft text-accent" },
  warning: { label: "Warning", icon: Warning, className: "bg-warn-soft text-warn" },
  critical: { label: "Critical", icon: WarningOctagon, className: "bg-bad-soft text-bad" },
};

export function Pill({ tone, className, label }: { tone: Tone; className?: string; label?: string }) {
  const I = tone.icon;
  return (
    <span className={cn("inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-xs font-medium", tone.className, className)}>
      <I size={14} weight="bold" aria-hidden />
      {label ?? tone.label}
    </span>
  );
}

export function StatusPill({ status, className }: { status: AttendanceStatus; className?: string }) {
  return <Pill tone={STATUS_TONE[status]} className={className} />;
}

export function SeverityPill({ severity, className }: { severity: Severity; className?: string }) {
  return <Pill tone={SEVERITY_TONE[severity]} className={className} />;
}
