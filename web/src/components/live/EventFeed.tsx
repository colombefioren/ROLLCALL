"use client";

import { ListBullets } from "@phosphor-icons/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { useLive } from "@/lib/live";
import type { Paged, RollEvent } from "@/lib/types";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Empty } from "@/components/ui/Empty";
import { RowsSkeleton } from "@/components/ui/Skeleton";
import { EventRow } from "./EventRow";

export function EventFeed() {
  const { data, isLoading } = useSWR<Paged<RollEvent>>("/events?limit=25", fetcher);
  const { subscribe } = useLive();
  const [pushed, setPushed] = useState<RollEvent[]>([]);

  useEffect(() => subscribe((ev) => setPushed((prev) => [ev, ...prev].slice(0, 25))), [subscribe]);

  const seen = new Set<number>();
  const items = [...pushed, ...(data?.items ?? [])].filter((ev) => (seen.has(ev.id) ? false : (seen.add(ev.id), true))).slice(0, 25);

  return (
    <Panel className="flex min-h-0 flex-col">
      <PanelHeader
        title="Activity"
        aside={
          <Link href="/logs" className="text-xs text-accent hover:underline">
            Full log
          </Link>
        }
      />
      {isLoading ? (
        <RowsSkeleton rows={6} />
      ) : items.length === 0 ? (
        <Empty icon={ListBullets} title="No activity yet" body="Check-ins, exits and alerts will show up here as they happen." />
      ) : (
        <ul className="scrollbar-thin max-h-[480px] overflow-y-auto">
          {items.map((ev) => (
            <EventRow key={ev.id} ev={ev} compact />
          ))}
        </ul>
      )}
    </Panel>
  );
}
