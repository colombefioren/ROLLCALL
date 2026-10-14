"use client";

import { Check, Checks, ShieldCheck } from "@phosphor-icons/react";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { fetcher, post } from "@/lib/api";
import type { RollEvent } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Empty } from "@/components/ui/Empty";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RowsSkeleton } from "@/components/ui/Skeleton";
import { EventRow } from "@/components/live/EventRow";
import { cn } from "@/components/ui/cn";

interface AlertsPayload {
  items: RollEvent[];
  unacknowledged: number;
}

export function AlertsView() {
  const [onlyOpen, setOnlyOpen] = useState(true);
  const key = `/alerts?limit=200${onlyOpen ? "&unacknowledged=true" : ""}`;
  const { data, isLoading } = useSWR<AlertsPayload>(key, fetcher);
  const refresh = () => mutate((k) => typeof k === "string" && (k.startsWith("/alerts") || k.startsWith("/stats")));

  const ack = async (id: number) => {
    await post(`/alerts/${id}/ack`);
    await refresh();
  };
  const ackAll = async () => {
    await post("/alerts/ack-all");
    await refresh();
  };

  const grouped = (data?.items ?? []).reduce<Record<string, RollEvent[]>>((acc, ev) => {
    (acc[ev.severity] ??= []).push(ev);
    return acc;
  }, {});
  const ordered = (["critical", "warning", "info"] as const).flatMap((s) => grouped[s] ?? []);

  return (
    <div className="flex flex-col gap-4 pb-16 md:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Alerts</h1>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border-strong p-0.5">
            {[
              { v: true, label: "Open" },
              { v: false, label: "All" },
            ].map((o) => (
              <button
                key={String(o.v)}
                onClick={() => setOnlyOpen(o.v)}
                className={cn("h-7 rounded px-2.5 text-xs font-medium", onlyOpen === o.v ? "bg-ink text-bg" : "text-ink-2")}
              >
                {o.label}
              </button>
            ))}
          </div>
          <Button size="sm" onClick={ackAll} disabled={!data?.unacknowledged}>
            <Checks size={14} weight="bold" /> Acknowledge all
          </Button>
        </div>
      </div>
      <Panel>
        <PanelHeader title={onlyOpen ? "Needs attention" : "Every alert"} aside={<span className="num text-xs text-muted">{data?.unacknowledged ?? 0} open</span>} />
        {isLoading ? (
          <RowsSkeleton rows={4} />
        ) : ordered.length === 0 ? (
          <Empty
            icon={ShieldCheck}
            title={onlyOpen ? "Nothing to review" : "No alerts recorded"}
            body="Unknown faces, a covered lens, overcrowding, duplicate faces and early exits all land here."
          />
        ) : (
          <ul>
            {ordered.map((ev) => (
              <EventRow key={ev.id} ev={ev}>
                <div className="mt-2 flex items-center gap-2">
                  {ev.acknowledged ? (
                    <span className="inline-flex items-center gap-1 text-xs text-muted">
                      <Check size={12} weight="bold" /> Acknowledged
                    </span>
                  ) : (
                    <Button size="sm" onClick={() => ack(ev.id)}>
                      <Check size={14} weight="bold" /> Acknowledge
                    </Button>
                  )}
                </div>
              </EventRow>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
