import type { components } from "./api-schema";
export type Budget = components["schemas"]["BudgetView"];
export type WorkerStatus = components["schemas"]["WorkerView"];
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
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
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
  let data;
  try {
    data = await response.json();
  } catch {
    throw new ApiError(
      "Server returned an unreadable response. Check its health and try again.",
      response.status,
    );
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      window.dispatchEvent(new Event("commander-session-expired"));
    }
    throw new ApiError(
      data.error?.message || "Request failed",
      response.status,
    );
  }
  return data as T;
}
export function when(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}
