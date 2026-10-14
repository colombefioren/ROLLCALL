"use client";

import { Eye } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useLive } from "@/lib/live";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { Empty } from "@/components/ui/Empty";
import { cn } from "@/components/ui/cn";

export function InFrame() {
  const { camera } = useLive();
  const reduce = useReducedMotion();
  const sightings = camera?.sightings ?? [];
  const known = sightings.filter((s) => s.student_id !== null);
  const unknown = sightings.length - known.length;
  // One row per student id so a duplicate match does not double-list.
  const rows = Array.from(new Map(known.map((s) => [s.student_id, s])).values());

  return (
    <Panel className="flex min-h-0 flex-1 flex-col">
      <PanelHeader
        title="In frame now"
        aside={
          <span className="num text-xs text-muted">
            {sightings.length} face{sightings.length === 1 ? "" : "s"}
            {unknown ? `, ${unknown} unknown` : ""}
          </span>
        }
      />
      {rows.length === 0 ? (
        <Empty icon={Eye} title={unknown ? "Only unrecognised faces" : "Nobody in frame"} body={unknown ? "Enroll them from the Students page." : undefined} />
      ) : (
        <ul className="scrollbar-thin flex-1 overflow-y-auto">
          <AnimatePresence initial={false}>
            {rows.map((s) => (
              <motion.li
                key={s.student_id}
                layout={!reduce}
                initial={reduce ? false : { opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reduce ? undefined : { opacity: 0, x: 8 }}
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-center gap-3 border-b border-border px-4 py-2.5 last:border-0"
              >
                <span className="size-2 rounded-full bg-good" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{s.name}</span>
                  <span className="num block text-xs text-muted">{s.code}</span>
                </span>
                <span className={cn("num text-xs", s.score > 0.6 ? "text-good" : "text-muted")}>{(s.score * 100).toFixed(0)}%</span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Panel>
  );
}
