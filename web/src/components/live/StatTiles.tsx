"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Stats } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/components/ui/cn";

const TILES: Array<{ key: "present" | "late" | "left" | "pending"; label: string; className: string }> = [
  { key: "present", label: "Present", className: "text-good" },
  { key: "late", label: "Late", className: "text-warn" },
  { key: "left", label: "Left", className: "text-neutral" },
  { key: "pending", label: "Not seen", className: "text-muted" },
];

export function StatTiles() {
  const { data: stats, isLoading } = useSWR<Stats>("/stats", fetcher);
  const hasSession = !!stats?.session;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {TILES.map((t) => (
        <div key={t.key} className="rounded-panel border border-border bg-surface px-4 py-3">
          <p className="text-xs font-medium text-muted">{t.label}</p>
          {isLoading ? (
            <Skeleton className="mt-1.5 h-7 w-12" />
          ) : (
            <p className={cn("num mt-0.5 text-2xl font-semibold leading-tight", hasSession ? t.className : "text-muted")}>
              {hasSession ? stats!.counts[t.key] : "0"}
            </p>
          )}
        </div>
      ))}
      <div className="rounded-panel border border-border bg-surface px-4 py-3">
        <p className="text-xs font-medium text-muted">Open alerts</p>
        {isLoading ? (
          <Skeleton className="mt-1.5 h-7 w-12" />
        ) : (
          <p className={cn("num mt-0.5 text-2xl font-semibold leading-tight", stats!.unacknowledged_alerts ? "text-bad" : "text-muted")}>
            {stats!.unacknowledged_alerts}
          </p>
        )}
      </div>
    </div>
  );
}
