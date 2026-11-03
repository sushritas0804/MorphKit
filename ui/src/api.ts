import type { ApplyResult, Preview, ProjectScan, SegmentManifest } from "./types";

const token = new URLSearchParams(window.location.search).get("t") ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "content-type": "application/json",
      "x-morphkit-token": token,
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
  }
  return body as T;
}

export const api = {
  project: () => request<ProjectScan>("/api/project"),
  segments: () => request<SegmentManifest[]>("/api/segments"),
  preview: (body: unknown) =>
    request<Preview>("/api/preview", { method: "POST", body: JSON.stringify(body) }),
  apply: (body: unknown) =>
    request<ApplyResult>("/api/apply", { method: "POST", body: JSON.stringify(body) }),
};
