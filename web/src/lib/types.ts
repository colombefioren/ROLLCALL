export type Severity = "info" | "warning" | "critical";
export type EventKind = "attendance" | "alert" | "system";
export type AttendanceStatus = "present" | "late" | "left" | "absent" | "pending";

export interface StudentMin {
  id: number;
  code: string;
  name: string;
  group: string;
  photo: string | null;
}

export interface Student extends StudentMin {
  templates: number;
  created_at: string;
}

export interface SessionInfo {
  id: number;
  name: string;
  started_at: string;
  planned_end_at: string | null;
  ended_at: string | null;
  grace_minutes: number;
  active: boolean;
}

export interface AttendanceRow {
  student: StudentMin;
  status: AttendanceStatus;
  arrived_late: boolean;
  checked_in_at: string | null;
  checked_out_at: string | null;
  last_seen_at: string | null;
  sightings: number;
  leaves: number;
  minutes_present: number;
}

export interface Sheet {
  session: SessionInfo;
  rows: AttendanceRow[];
  counts: Record<AttendanceStatus, number>;
}

export interface RollEvent {
  id: number;
  ts: string;
  kind: EventKind;
  type: string;
  severity: Severity;
  message: string;
  session_id: number | null;
  student_id: number | null;
  snapshot: string | null;
  payload: Record<string, unknown>;
  acknowledged: boolean;
  student?: { name: string; code: string; photo: string | null } | null;
}

export interface Sighting {
  student_id: number | null;
  name: string;
  code: string | null;
  score: number;
  box: [number, number, number, number];
}

export interface CameraStatus {
  camera_ok: boolean;
  camera_blocked: boolean;
  brightness: number;
  fps: number;
  faces: number;
  sightings: Sighting[];
  gallery_size: number;
  source: string;
}

export interface Stats {
  session: { id: number; name: string; started_at: string; planned_end_at: string | null; grace_minutes: number } | null;
  counts: Record<AttendanceStatus, number>;
  enrolled: number;
  unacknowledged_alerts: number;
  camera: CameraStatus;
}

export interface Paged<T> {
  items: T[];
  next_before: number | null;
}
