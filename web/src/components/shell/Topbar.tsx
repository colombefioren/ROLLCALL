"use client";

import { Moon, Sun, VideoCamera, VideoCameraSlash, WifiSlash } from "@phosphor-icons/react";
import { useEffect, useState, useSyncExternalStore } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { useLive } from "@/lib/live";
import { fmtDuration } from "@/lib/format";
import type { Stats } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { MobileNav } from "./Sidebar";

function useNow(tick = 1000) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const update = () => setNow(Date.now());
    const first = setTimeout(update, 0);
    const id = setInterval(update, tick);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [tick]);
  return now;
}

function subscribeTheme(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => obs.disconnect();
}

function ThemeToggle() {
  const dark = useSyncExternalStore(
    subscribeTheme,
    () => document.documentElement.classList.contains("dark"),
    () => false,
  );
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("rollcall-theme", next ? "dark" : "light");
    } catch {}
  };
  return (
    <Button variant="ghost" size="sm" onClick={toggle} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
      {dark ? <Sun size={16} /> : <Moon size={16} />}
    </Button>
  );
}

export function Topbar() {
  const { connected, camera } = useLive();
  const { data: stats } = useSWR<Stats>("/stats", fetcher, { refreshInterval: 15000 });
  const now = useNow();
  const session = stats?.session ?? null;
  const elapsed = session && now ? (now - new Date(session.started_at).getTime()) / 1000 : 0;
  const cameraOk = connected && camera?.camera_ok && !camera.camera_blocked;

  return (
    <>
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-surface/90 px-4 backdrop-blur md:px-6">
        <div className="flex min-w-0 items-center gap-2 md:hidden">
          <span className="text-[15px] font-semibold tracking-tight">Rollcall</span>
        </div>
        <div className="hidden min-w-0 items-center gap-2 md:flex">
          {session ? (
            <>
              <span className="truncate text-sm font-medium">{session.name}</span>
              <span className="num rounded-md bg-good-soft px-1.5 py-0.5 text-xs font-medium text-good">{fmtDuration(elapsed)}</span>
            </>
          ) : (
            <span className="text-sm text-muted">No session running</span>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span
            className={cn(
              "inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-xs font-medium",
              !connected ? "bg-neutral-soft text-muted" : cameraOk ? "bg-good-soft text-good" : "bg-bad-soft text-bad",
            )}
          >
            {!connected ? <WifiSlash size={14} weight="bold" /> : cameraOk ? <VideoCamera size={14} weight="bold" /> : <VideoCameraSlash size={14} weight="bold" />}
            {!connected ? "Server offline" : cameraOk ? `Camera live` : camera?.camera_blocked ? "Camera blocked" : "No camera"}
            {connected && camera && cameraOk ? <span className="num hidden text-muted sm:inline">{camera.fps.toFixed(0)} fps</span> : null}
          </span>
          <ThemeToggle />
        </div>
      </header>
      <MobileNav />
    </>
  );
}
