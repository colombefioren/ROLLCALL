"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Broadcast, ClipboardText, ListBullets, Siren, Users, type Icon } from "@phosphor-icons/react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { Stats } from "@/lib/types";
import { cn } from "@/components/ui/cn";

const NAV: Array<{ href: string; label: string; icon: Icon }> = [
  { href: "/", label: "Live", icon: Broadcast },
  { href: "/attendance", label: "Attendance", icon: ClipboardText },
  { href: "/alerts", label: "Alerts", icon: Siren },
  { href: "/logs", label: "Logs", icon: ListBullets },
  { href: "/students", label: "Students", icon: Users },
];

export function Sidebar() {
  const path = usePathname();
  const { data: stats } = useSWR<Stats>("/stats", fetcher, { refreshInterval: 15000 });
  const unacked = stats?.unacknowledged_alerts ?? 0;
  return (
    <aside className="sticky top-0 hidden h-dvh w-56 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-14 items-center gap-2 px-4">
        <span className="grid size-7 place-items-center rounded-md bg-accent text-accent-ink">
          <Broadcast size={16} weight="bold" aria-hidden />
        </span>
        <span className="text-[15px] font-semibold tracking-tight">Rollcall</span>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 px-2 pt-2">
        {NAV.map(({ href, label, icon: I }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-sm transition-colors",
                active ? "bg-accent-soft font-medium text-accent" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
              )}
            >
              <I size={18} weight={active ? "fill" : "regular"} aria-hidden />
              {label}
              {href === "/alerts" && unacked > 0 ? (
                <span className="num ml-auto rounded-md bg-bad-soft px-1.5 py-0.5 text-[11px] font-semibold text-bad">{unacked}</span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <p className="px-4 pb-4 text-[11px] text-muted">
        {stats ? `${stats.enrolled} enrolled` : ""}
      </p>
    </aside>
  );
}

export function MobileNav() {
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface md:hidden">
      {NAV.map(({ href, label, icon: I }) => {
        const active = href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link key={href} href={href} className={cn("flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px]", active ? "text-accent" : "text-muted")}>
            <I size={20} weight={active ? "fill" : "regular"} aria-hidden />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
