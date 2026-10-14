import type { Icon } from "@phosphor-icons/react";
import type { ReactNode } from "react";

export function Empty({ icon: I, title, body, action }: { icon: Icon; title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-14 text-center">
      <I size={28} className="text-muted" aria-hidden />
      <p className="text-sm font-medium text-ink">{title}</p>
      {body ? <p className="max-w-[40ch] text-[13px] text-muted">{body}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
