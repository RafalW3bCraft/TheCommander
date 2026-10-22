export type Memory = {
  id: string;
  kind: string;
  key: string;
  content: string;
  source: string;
  observed_at: string;
  updated_at: string;
  revision: number;
  expires_at: string | null;
};
export type Run = {
  id: string;
  skill: string;
  prompt: string;
  status: string;
  result: string | null;
  error: string | null;
  created_at: string;
  conversation_id: string | null;
};
export type Action = {
  id: string;
  tool: string;
  status: string;
  arguments: { repository: string; title: string; body: string };
  args_hash: string;
  expires_at: string;
  receipt: { url: string; verified_at: string } | null;
  error: string | null;
};
export type Detail = Run & {
  events: { id: number; kind: string; created_at: string; payload: unknown }[];
  actions: Action[];
  evidence: {
    id: string;
    url: string;
    title: string;
    excerpt: string;
    fetched_at: string;
  }[];
};
export type Connection = {
  kind: string;
  status: string;
  revision: number;
  validated_at: string | null;
  detail: string | null;
  config: {
    repository?: string;
    domains?: string[];
    enabled?: boolean;
    model?: string;
    endpoint?: string;
  };
};
export type Skill = {
  id: string;
  name: string;
  purpose: string;
  version: string;
  tools: string[];
  example: string;
  hash: string;
};
export type Schedule = {
  id: string;
  skill: string;
  prompt: string;
  timezone: string;
  next_at: string | null;
  interval_seconds: number | null;
  paused: boolean;
  revision: number;
  last_at: string | null;
};
export type User = { username: string; owner_id: string; csrf: string };
export type Conversation = { id: string; title: string; created_at: string };
export type Message = {
  id: number;
  role: string;
  content: string;
  created_at: string;
};
let csrf = "";
export function setCSRF(value: string) {
  csrf = value;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || "Request failed");
  return data as T;
}
export function when(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}
