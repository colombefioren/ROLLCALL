"use client";

import { Play, Stop } from "@phosphor-icons/react";
import { useState } from "react";
import useSWR, { mutate } from "swr";
import { ApiError, fetcher, post } from "@/lib/api";
import { fmtTime } from "@/lib/format";
import type { Stats } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";

export function SessionControl() {
  const { data: stats } = useSWR<Stats>("/stats", fetcher);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [grace, setGrace] = useState(10);
  const [duration, setDuration] = useState(60);
  const session = stats?.session ?? null;

  const refresh = () => mutate((k) => typeof k === "string" && (k.startsWith("/stats") || k.startsWith("/sessions")));

  const start = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/sessions", { name: name.trim() || "Class", grace_minutes: grace, duration_minutes: duration || null });
      setOpen(false);
      setName("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the session");
    } finally {
      setBusy(false);
    }
  };

  const end = async () => {
    if (!confirm("End the session? Students not seen will be marked absent.")) return;
    setBusy(true);
    try {
      await post("/sessions/end");
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  if (session) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted">
          Started {fmtTime(session.started_at)}
          {session.planned_end_at ? `, ends ${fmtTime(session.planned_end_at)}` : ""}, {session.grace_minutes} min grace
        </span>
        <Button variant="danger" size="sm" onClick={end} disabled={busy}>
          <Stop size={14} weight="fill" /> End session
        </Button>
      </div>
    );
  }

  return (
    <>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        <Play size={14} weight="fill" /> Start session
      </Button>
      <Modal open={open} onClose={() => setOpen(false)} title="Start a session">
        <form onSubmit={start} className="flex flex-col gap-4">
          <Field label="Session name">
            <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Algorithms, group B" maxLength={80} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Late after (min)" hint="Check-ins after this are marked late">
              <Input type="number" min={0} max={120} value={grace} onChange={(e) => setGrace(Number(e.target.value))} />
            </Field>
            <Field label="Duration (min)" hint="Used to flag early leavers">
              <Input type="number" min={5} max={600} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
            </Field>
          </div>
          {error ? <p className="text-sm text-bad">{error}</p> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Starting" : "Start"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
