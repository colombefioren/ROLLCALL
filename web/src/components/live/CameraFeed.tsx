"use client";

import { VideoCameraSlash } from "@phosphor-icons/react";
import { API_URL } from "@/lib/api";
import { useLive } from "@/lib/live";

export function CameraFeed() {
  const { connected, generation: nonce, camera } = useLive();
  const ready = connected && camera?.camera_ok;

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-panel border border-border bg-[#0b0b0d]">
      {ready ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={nonce} src={`${API_URL}/stream.mjpg?n=${nonce}`} alt="Live classroom camera" className="size-full object-contain" />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center text-[#8c8c96]">
          <VideoCameraSlash size={28} aria-hidden />
          <p className="text-sm">{connected ? "Camera is not delivering frames" : "Waiting for the vision server"}</p>
          <p className="max-w-[36ch] text-xs">{connected ? `Source: ${camera?.source ?? "?"}` : "Start it with uvicorn rollcall.main:app"}</p>
        </div>
      )}
      {camera?.camera_blocked ? (
        <div className="absolute inset-x-0 top-0 bg-bad px-3 py-1.5 text-center text-xs font-semibold text-white">Camera blocked</div>
      ) : null}
    </div>
  );
}
