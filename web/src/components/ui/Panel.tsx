import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <section className={cn("rounded-panel border border-border bg-surface shadow-(--shadow)", className)} {...props} />;
}

export function PanelHeader({ title, aside, className }: { title: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex h-12 items-center justify-between gap-3 border-b border-border px-4", className)}>
      <h2 className="text-sm font-semibold text-ink">{title}</h2>
      {aside ? <div className="flex items-center gap-2">{aside}</div> : null}
    </header>
  );
}
