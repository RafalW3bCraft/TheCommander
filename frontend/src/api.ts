import type { components } from "./api-schema";
export type Memory = components["schemas"]["MemoryView"];
export type Run = components["schemas"]["RunView"];
export type Action = components["schemas"]["ActionView"];
export type Detail = components["schemas"]["RunDetailView"];
export type Connection = components["schemas"]["ConnectionView"];
export type Skill = components["schemas"]["SkillView"];
export type Schedule = components["schemas"]["ScheduleView"];
export type User = components["schemas"]["UserView"];
export type Conversation = components["schemas"]["ConversationView"];
export type Message = components["schemas"]["MessageView"];
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
