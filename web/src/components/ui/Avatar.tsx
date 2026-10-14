import { assetUrl } from "@/lib/api";
import { cn } from "./cn";

export function Avatar({ name, photo, size = 32, className }: { name: string; photo?: string | null; size?: number; className?: string }) {
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
  const src = assetUrl(photo);
  if (src) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="" width={size} height={size} className={cn("shrink-0 rounded-full object-cover", className)} style={{ width: size, height: size }} />;
  }
  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center rounded-full bg-neutral-soft text-[11px] font-semibold text-ink-2", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {initials}
    </span>
  );
}
