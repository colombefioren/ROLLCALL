"use client";

import { Camera, Plus, Trash, UploadSimple, UserPlus, Users } from "@phosphor-icons/react";
import { useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import useSWR, { mutate } from "swr";
import { ApiError, del, fetcher, post, postForm } from "@/lib/api";
import { useLive } from "@/lib/live";
import type { Student } from "@/lib/types";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Empty } from "@/components/ui/Empty";
import { Field, Input } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/components/ui/cn";

function refreshStudents() {
  return mutate((k) => typeof k === "string" && (k.startsWith("/students") || k.startsWith("/stats")));
}

function NewStudent({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [group, setGroup] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/students", { code, name, group });
      await refreshStudents();
      setCode("");
      setName("");
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add the student");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} onClose={onClose} title="Add a student">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid grid-cols-[120px_1fr] gap-3">
          <Field label="Code">
            <Input autoFocus value={code} onChange={(e) => setCode(e.target.value)} placeholder="S042" required maxLength={32} />
          </Field>
          <Field label="Full name">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Tiana Rakoto" required maxLength={80} />
          </Field>
        </div>
        <Field label="Group" hint="Optional">
          <Input value={group} onChange={(e) => setGroup(e.target.value)} placeholder="L3 Info" maxLength={40} />
        </Field>
        {error ? <p className="text-sm text-bad">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Adding" : "Add student"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function StudentCard({ s, focused }: { s: Student; focused: boolean }) {
  const { camera, connected } = useLive();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"upload" | "capture" | "delete" | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const facesNow = camera?.faces ?? 0;

  const run = async (what: "upload" | "capture" | "delete", fn: () => Promise<unknown>, okText?: string) => {
    setBusy(what);
    setMsg(null);
    try {
      await fn();
      await refreshStudents();
      if (okText) setMsg({ ok: true, text: okText });
    } catch (err) {
      setMsg({ ok: false, text: err instanceof ApiError ? err.message : "Request failed" });
    } finally {
      setBusy(null);
    }
  };

  const onFile = (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("image", file);
    run("upload", () => postForm(`/students/${s.id}/enroll`, form), "Photo enrolled");
  };

  return (
    <li className={cn("flex flex-col gap-3 rounded-panel border bg-surface p-4", focused ? "border-accent" : "border-border")}>
      <div className="flex items-center gap-3">
        <Avatar name={s.name} photo={s.photo} size={44} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{s.name}</p>
          <p className="num truncate text-xs text-muted">
            {s.code}
            {s.group ? ` · ${s.group}` : ""}
          </p>
        </div>
        <span className={cn("num shrink-0 rounded-md px-1.5 py-0.5 text-xs font-medium", s.templates ? "bg-good-soft text-good" : "bg-warn-soft text-warn")}>
          {s.templates ? `${s.templates} face${s.templates > 1 ? "s" : ""}` : "not enrolled"}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
        <Button size="sm" onClick={() => fileRef.current?.click()} disabled={busy !== null}>
          <UploadSimple size={14} weight="bold" /> {busy === "upload" ? "Enrolling" : "Photo"}
        </Button>
        <Button
          size="sm"
          onClick={() => run("capture", () => post(`/students/${s.id}/enroll/capture`), "Captured from camera")}
          disabled={busy !== null || !connected || facesNow === 0}
          title={facesNow === 0 ? "Nobody in front of the camera" : `${facesNow} face(s) in frame, largest one is used`}
        >
          <Camera size={14} weight="bold" /> {busy === "capture" ? "Capturing" : "Capture"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto text-muted hover:text-bad"
          aria-label={`Remove ${s.name}`}
          disabled={busy !== null}
          onClick={() => confirm(`Remove ${s.name} and their face templates?`) && run("delete", () => del(`/students/${s.id}`))}
        >
          <Trash size={14} />
        </Button>
      </div>
      {msg ? <p className={cn("text-xs", msg.ok ? "text-good" : "text-bad")}>{msg.text}</p> : null}
    </li>
  );
}

export function StudentsView() {
  const { data, isLoading } = useSWR<Student[]>("/students", fetcher);
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const focus = Number(useSearchParams().get("focus") ?? 0);
  const list = (data ?? []).filter((s) => !q || `${s.name} ${s.code} ${s.group}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="flex flex-col gap-4 pb-16 md:pb-0">
      <NewStudent open={open} onClose={() => setOpen(false)} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Students</h1>
        <div className="flex items-center gap-2">
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter" className="w-44" aria-label="Filter students" />
          <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
            <Plus size={14} weight="bold" /> Add student
          </Button>
        </div>
      </div>
      <Panel>
        <PanelHeader title="Roster" aside={<span className="num text-xs text-muted">{data ? `${data.filter((s) => s.templates).length} of ${data.length} enrolled` : ""}</span>} />
        {isLoading ? (
          <ul className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <li key={i} className="rounded-panel border border-border p-4">
                <div className="flex items-center gap-3">
                  <Skeleton className="size-11 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-3.5 w-32" />
                    <Skeleton className="mt-2 h-3 w-16" />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : list.length === 0 ? (
          <Empty
            icon={data?.length ? Users : UserPlus}
            title={data?.length ? "No student matches" : "No students yet"}
            body={data?.length ? undefined : "Add a student, then enroll a face from a photo or straight from the camera."}
            action={data?.length ? undefined : <Button variant="primary" size="sm" onClick={() => setOpen(true)}>Add student</Button>}
          />
        ) : (
          <ul className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {list.map((s) => (
              <StudentCard key={s.id} s={s} focused={s.id === focus} />
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
