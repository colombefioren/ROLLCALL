"use client";

import Link from "next/link";
import { assetUrl } from "@/lib/api";
import { eventLabel, fmtTime } from "@/lib/format";
import type { RollEvent } from "@/lib/types";
import { SEVERITY_TONE } from "@/components/ui/Status";
import { cn } from "@/components/ui/cn";

export function EventRow({ ev, compact = false, children }: { ev: RollEvent; compact?: boolean; children?: React.ReactNode }) {
  const tone = SEVERITY_TONE[ev.severity];
  const I = tone.icon;
  const snap = assetUrl(ev.snapshot);
  return (
    <li className={cn("flex gap-3 border-b border-border px-4 last:border-0", compact ? "py-2" : "py-3")}>
      <span className={cn("mt-0.5 grid size-6 shrink-0 place-items-center rounded-md", tone.className)}>
        <I size={14} weight="bold" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs font-medium text-ink-2">{eventLabel(ev.type)}</span>
          <span className="num ml-auto shrink-0 text-xs text-muted">{fmtTime(ev.ts, !compact)}</span>
        </div>
        <p className={cn("text-ink", compact ? "truncate text-[13px]" : "text-sm")}>{ev.message}</p>
        {!compact && ev.student ? (
          <Link href={`/students?focus=${ev.student_id}`} className="num text-xs text-accent hover:underline">
            {ev.student.code}
          </Link>
        ) : null}
        {children}
      </div>
      {!compact && snap ? (
        <a href={snap} target="_blank" rel="noreferrer" className="shrink-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={snap} alt="Snapshot" className="h-14 w-20 rounded-md border border-border object-cover" />
        </a>
      ) : null}
    </li>
  );
}
