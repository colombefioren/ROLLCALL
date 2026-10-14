export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parse<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(API_URL + path, { cache: "no-store" });
  return parse<T>(res);
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(API_URL + path, {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return parse<T>(res);
}

export async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(API_URL + path, { method: "POST", body: form });
  return parse<T>(res);
}

export async function del(path: string): Promise<void> {
  const res = await fetch(API_URL + path, { method: "DELETE" });
  await parse<void>(res);
}

export function assetUrl(path: string | null | undefined): string | undefined {
  return path ? API_URL + path : undefined;
}
