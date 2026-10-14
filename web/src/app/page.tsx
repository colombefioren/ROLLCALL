import { CameraFeed } from "@/components/live/CameraFeed";
import { EventFeed } from "@/components/live/EventFeed";
import { InFrame } from "@/components/live/InFrame";
import { SessionControl } from "@/components/live/SessionControl";
import { StatTiles } from "@/components/live/StatTiles";

export default function LivePage() {
  return (
    <div className="flex flex-col gap-4 pb-16 md:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Live</h1>
        <SessionControl />
      </div>
      <StatTiles />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-4">
          <CameraFeed />
          <EventFeed />
        </div>
        <div className="flex min-h-[320px] flex-col gap-4">
          <InFrame />
        </div>
      </div>
    </div>
  );
}
