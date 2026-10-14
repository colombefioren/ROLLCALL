"use client";

import { ListBullets, MagnifyingGlass } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { EventKind, Paged, RollEvent, SessionInfo, Severity } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Empty } from "@/components/ui/Empty";
import { Input, Select } from "@/components/ui/Field";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { RowsSkeleton } from "@/components/ui/Skeleton";
import { EventRow } from "@/components/live/EventRow";

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export function LogsView() {
  const [kind, setKind] = useState<EventKind | "">("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [session, setSession] = useState<string>("");
  const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const [olderPages, setOlderPages] = useState<{ key: string; items: RollEvent[] }>({ key: "", items: [] });
  const [loadingMore, setLoadingMore] = useState(false);
  const { data: sessions } = useSWR<SessionInfo[]>("/sessions", fetcher);

  const params = new URLSearchParams({ limit: "100" });
  if (kind) params.set("kind", kind);
  if (severity) params.set("severity", severity);
  if (session) params.set("session_id", session);
  if (dq) params.set("q", dq);
  const key = `/events?${params}`;
  const { data, isLoading } = useSWR<Paged<RollEvent>>(key, fetcher);

  const older = olderPages.key === key ? olderPages.items : [];
  const [exhausted, setExhausted] = useState<string | null>(null);

  const loadMore = async () => {
    const last = older.length ? older[older.length - 1] : data?.items[data.items.length - 1];
    if (!last) return;
    setLoadingMore(true);
    try {
      const page = await fetcher<Paged<RollEvent>>(`${key}&before=${last.id}`);
      setOlderPages({ key, items: [...older, ...page.items] });
      if (page.next_before === null) setExhausted(key);
    } finally {
      setLoadingMore(false);
    }
  };

  const items = [...(data?.items ?? []), ...older];
  const hasMore = data?.next_before !== null && exhausted !== key;

  return (
    <div className="flex flex-col gap-4 pb-16 md:pb-0">
      <h1 className="text-lg font-semibold tracking-tight">Logs</h1>
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_150px_150px_200px]">
        <div className="relative">
          <MagnifyingGlass size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search messages" className="pl-9" aria-label="Search" />
        </div>
        <Select value={kind} onChange={(e) => setKind(e.target.value as EventKind | "")} aria-label="Kind">
          <option value="">All kinds</option>
          <option value="attendance">Attendance</option>
          <option value="alert">Alerts</option>
          <option value="system">System</option>
        </Select>
        <Select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")} aria-label="Severity">
          <option value="">Any severity</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </Select>
        <Select value={session} onChange={(e) => setSession(e.target.value)} aria-label="Session">
          <option value="">All sessions</option>
          {sessions?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
      </div>
      <Panel>
        <PanelHeader title="Event log" aside={<span className="num text-xs text-muted">{items.length} shown</span>} />
        {isLoading ? (
          <RowsSkeleton rows={8} />
        ) : items.length === 0 ? (
          <Empty icon={ListBullets} title="No events match" body="Clear a filter or wait for the camera to see someone." />
        ) : (
          <>
            <ul>
              {items.map((ev) => (
                <EventRow key={ev.id} ev={ev} />
              ))}
            </ul>
            {hasMore ? (
              <div className="border-t border-border p-3 text-center">
                <Button size="sm" onClick={loadMore} disabled={loadingMore}>
                  {loadingMore ? "Loading" : "Load older"}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </Panel>
    </div>
  );
}
