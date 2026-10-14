"use client";

import { ClipboardText, DownloadSimple } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { API_URL, fetcher } from "@/lib/api";
import { fmtDateTime, fmtMinutes, fmtTime } from "@/lib/format";
import type { AttendanceStatus, SessionInfo, Sheet } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Empty } from "@/components/ui/Empty";
import { Select } from "@/components/ui/Field";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RowsSkeleton } from "@/components/ui/Skeleton";
import { STATUS_TONE, StatusPill } from "@/components/ui/Status";
import { cn } from "@/components/ui/cn";

const FILTERS: Array<{ key: AttendanceStatus | "all"; label: string }> = [
  { key: "all", label: "All" },
  { key: "present", label: "Present" },
  { key: "late", label: "Late" },
  { key: "left", label: "Left" },
  { key: "pending", label: "Not seen" },
  { key: "absent", label: "Absent" },
];

export function AttendanceView() {
  const { data: sessions } = useSWR<SessionInfo[]>("/sessions", fetcher);
  const [picked, setPicked] = useState<number | "active">("active");
  const key = picked === "active" ? "/sessions/active" : `/sessions/${picked}`;
  const { data: sheet, isLoading } = useSWR<Sheet | null>(key, fetcher, { refreshInterval: picked === "active" ? 5000 : 0 });
  const [filter, setFilter] = useState<AttendanceStatus | "all">("all");

  const rows = useMemo(() => (sheet ? sheet.rows.filter((r) => filter === "all" || r.status === filter) : []), [sheet, filter]);
  const active = sessions?.find((s) => s.active);

  return (
    <div className="flex flex-col gap-4 pb-16 md:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Attendance</h1>
        <div className="flex items-center gap-2">
          <Select value={picked} onChange={(e) => setPicked(e.target.value === "active" ? "active" : Number(e.target.value))} className="w-64" aria-label="Session">
            <option value="active">{active ? `Current: ${active.name}` : "Current session (none)"}</option>
            {sessions
              ?.filter((s) => !s.active)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}, {fmtDateTime(s.started_at)}
                </option>
              ))}
          </Select>
          {sheet ? (
            <Button size="sm" onClick={() => window.open(`${API_URL}/sessions/${sheet.session.id}/attendance.csv`, "_blank")}>
              <DownloadSimple size={14} weight="bold" /> CSV
            </Button>
          ) : null}
        </div>
      </div>

      <Panel>
        <PanelHeader
          title={sheet ? `${sheet.session.name}, ${fmtDateTime(sheet.session.started_at)}` : "Sheet"}
          aside={
            <div className="flex flex-wrap gap-1">
              {FILTERS.map((f) => {
                const n = f.key === "all" ? sheet?.rows.length : sheet?.counts[f.key];
                if (f.key !== "all" && !n) return null;
                return (
                  <button
                    key={f.key}
                    onClick={() => setFilter(f.key)}
                    className={cn(
                      "num h-7 rounded-md px-2 text-xs font-medium transition-colors",
                      filter === f.key ? "bg-ink text-bg" : "text-ink-2 hover:bg-surface-2",
                    )}
                  >
                    {f.label} {n ?? 0}
                  </button>
                );
              })}
            </div>
          }
        />
        {isLoading ? (
          <RowsSkeleton rows={8} />
        ) : !sheet ? (
          <Empty icon={ClipboardText} title="No session running" body="Start one from the Live page and the sheet fills itself as students walk in." />
        ) : rows.length === 0 ? (
          <Empty icon={ClipboardText} title="Nobody in this filter" />
        ) : (
          <div className="scrollbar-thin overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="px-4 py-2 font-medium">Student</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">In</th>
                  <th className="px-3 py-2 font-medium">Out</th>
                  <th className="px-3 py-2 font-medium">Time in room</th>
                  <th className="px-3 py-2 font-medium">Last seen</th>
                  <th className="px-3 py-2 text-right font-medium">Exits</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.student.id} className="border-t border-border">
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={r.student.name} photo={r.student.photo} size={28} />
                        <div className="min-w-0">
                          <div className="truncate font-medium">{r.student.name}</div>
                          <div className="num text-xs text-muted">
                            {r.student.code}
                            {r.student.group ? ` · ${r.student.group}` : ""}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <StatusPill status={r.status} />
                      {r.status === "present" && r.arrived_late ? <span className="ml-1 text-xs text-warn">arrived late</span> : null}
                    </td>
                    <td className="num px-3 py-2">{fmtTime(r.checked_in_at) || "-"}</td>
                    <td className="num px-3 py-2">{fmtTime(r.checked_out_at) || "-"}</td>
                    <td className="num px-3 py-2">{r.checked_in_at ? fmtMinutes(r.minutes_present) : "-"}</td>
                    <td className="num px-3 py-2 text-muted">{fmtTime(r.last_seen_at, true) || "-"}</td>
                    <td className={cn("num px-3 py-2 text-right", r.leaves ? "text-ink" : "text-muted")}>{r.leaves}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
      {sheet ? (
        <p className="text-xs text-muted">
          {Object.entries(STATUS_TONE)
            .filter(([k]) => sheet.counts[k as AttendanceStatus])
            .map(([k, t]) => `${sheet.counts[k as AttendanceStatus]} ${t.label.toLowerCase()}`)
            .join(", ")}
          . Students are marked as left after 45 s out of view and come back automatically.
        </p>
      ) : null}
    </div>
  );
}
