import { useCallback, useEffect, useRef, useState } from "react";
import { api, when } from "./api";
import type { Project } from "./ProjectSelector";

type SandboxStatus = {
  enabled: boolean;
  worker_online: boolean;
  model: string;
  vision_model: string;
  domains: string[];
  runtime: string;
};
type SandboxJob = {
  id: string;
  project_id: string;
  kind: "code" | "browser";
  goal: string;
  url: string;
  status: string;
  error: string | null;
  created_at: string;
  approval_digest: string | null;
  approval_expires_at: string | null;
  plan?: { explanation: string; code?: string; steps?: unknown[] } | null;
  evidence?: {
    stdout?: string;
    stderr?: string;
    screenshot?: string;
    screenshot_sha256?: string;
    text?: string;
    url?: string;
    verification?: { verified: boolean; explanation: string };
  };
  approval_snapshot?: {
    observed_url?: string;
    screenshot?: string;
    authorization?: {
      method: string;
      url: string;
      body: string;
      headers: Record<string, string>;
      operation_id: string;
    };
  };
  receipt?: Record<string, unknown>;
  events?: { kind: string; at?: string }[];
  calls?: {
    id: string;
    phase: string;
    provider: string;
    model: string;
    latency_ms: number;
    tokens: number | null;
    cost_usd: number | string | null;
    usage_status: string;
    created_at: string;
  }[];
};
type Artifact = { id: string; name: string; size: number; media_type: string };
const active = new Set(["queued", "running", "approved"]);
export function SandboxPage({ initialKind = "code" }: { initialKind?: "code" | "browser" }) {
  const refreshVersion = useRef(0);
  const [status, setStatus] = useState<SandboxStatus | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState("");
  const [kind, setKind] = useState<"code" | "browser">(initialKind);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [jobs, setJobs] = useState<SandboxJob[]>([]);
  const [selected, setSelected] = useState<SandboxJob | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [password, setPassword] = useState("");
  useEffect(() => {
    setReviewed(false);
    setPassword("");
  }, [selected?.id, selected?.approval_digest]);
  const action = async (fn: () => Promise<void>) => {
    setError("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sandbox request failed");
    } finally {
      setBusy(false);
    }
  };
  const refresh = useCallback(async () => {
    const version = ++refreshVersion.current;
    const [freshStatus, freshJobs] = await Promise.all([
      api<SandboxStatus>("/sandbox/status"),
      project
        ? api<SandboxJob[]>("/sandbox/jobs?project_id=" + project)
        : Promise.resolve([]),
    ]);
    if (version === refreshVersion.current) {
      setStatus(freshStatus);
      setJobs(freshJobs);
    }
  }, [project]);
  useEffect(() => {
    let disposed = false;
    void api<Project[]>("/projects")
      .then((items) => {
        if (!disposed) {
          setProjects(items);
          setProject(items[0]?.id ?? "");
        }
      })
      .catch((e: Error) => !disposed && setError(e.message));
    return () => {
      disposed = true;
    };
  }, []);
  useEffect(() => {
    let disposed = false;
    const poll = async () => {
      try {
        await refresh();
        if (selected?.id && !disposed) {
          const [detail, files] = await Promise.all([
            api<SandboxJob>("/sandbox/jobs/" + selected.id),
            api<Artifact[]>("/sandbox/jobs/" + selected.id + "/artifacts"),
          ]);
          if (!disposed) {
            setSelected(detail);
            setArtifacts(files);
          }
        }
      } catch (e) {
        if (!disposed)
          setError(e instanceof Error ? e.message : "Refresh failed");
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 2500);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [refresh, selected?.id]);
  const decision = (approve: boolean) =>
    action(async () => {
      if (!selected) return;
      if (approve) {
        await api("/auth/reauthenticate", "POST", { password });
        setPassword("");
      }
      const result = await api<SandboxJob>(
        "/sandbox/jobs/" + selected.id + "/decision",
        "POST",
        { digest: selected.approval_digest, approve },
      );
      setSelected(result);
      setReviewed(false);
      await refresh();
    });
  return (
    <div className="sandbox-workspace">
      <p className="eyebrow">BLAST RADIUS ZERO · VULTR</p>
      <p>
        Ask for a result. Inspect the generated plan, execution receipt and
        verification. Code runs offline. A browser write requires review of the
        exact request, screenshot and verification before your approval.
        Use public, non-sensitive tasks and an operator-approved site.
      </p>
      <div className="sandbox-health" role="status">
        {status?.enabled ? "Execution enabled" : "Execution disabled"} ·{" "}
        {status?.worker_online ? "Runner online" : "Runner offline"} ·{" "}
        {status?.model || "Vultr model not configured"}
        {status && <small className="sandbox-capabilities">Runtime: {status.runtime} · Vision model: {status.vision_model || "Not configured"}</small>}
      </div>
      {status && (!status.enabled || !status.worker_online) && <p>
        {!status.enabled ? "The operator must verify containment and enable execution before tasks can run." : "The runner is unavailable. Ask the operator to check the worker service; no new task can start here."}
      </p>}
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          void action(async () => {
            const job = await api<SandboxJob>("/sandbox/jobs", "POST", {
              project_id: project,
              kind,
              goal: String(data.get("goal")),
              url: kind === "browser" ? String(data.get("url")) : "",
            });
            setSelected(job);
            await refresh();
          });
        }}
      >
        <h2>New sandbox task</h2>
        {!projects.length && <p>Create your first project in Assistant before starting a sandbox task.</p>}
        <label>
          Project
          <select
            value={project}
            onChange={(e) => {
              setProject(e.target.value);
              setSelected(null);
              setArtifacts([]);
            }}
            required
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Execution pattern
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as "code" | "browser")}
          >
            <option value="code">Sandboxed Python</option>
            <option value="browser">Sandboxed browser</option>
          </select>
        </label>
        <label>
          Goal
          <textarea
            name="goal"
            required
            minLength={3}
            maxLength={4000}
            rows={4}
            placeholder={
              kind === "code"
                ? "Calculate the mean, median and standard deviation of [8, 12, 19, 21, 25]. Print the results."
                : "Inspect this page and prepare the form actions for my approval."
            }
          />
        </label>
        <p className="muted">{kind === "code" ? "Example: calculate the mean of [8, 12, 19, 21, 25] and save the results as a CSV in /output." : "Start with a read-only task on an approved public page. Writes are limited to the operator’s controlled fixture."}</p>
        {kind === "browser" && (
          <label>
            Starting HTTPS URL
            <input
              name="url"
              type="url"
              required
              maxLength={2000}
              placeholder="https://example.com"
            />
            <small>
              Exact approved domains:{" "}
              {status?.domains.join(", ") || "None configured"}. Do not enter
              passwords or payment information.
            </small>
          </label>
        )}
        <button
          disabled={
            busy || !project || !status?.enabled || !status.worker_online
          }
        >
          {busy ? "Submitting…" : kind === "code" ? "Run code" : "Inspect browser task"}
        </button>
      </form>
      <div className="sandbox-columns">
        <section aria-label="Sandbox task history" className="card">
          <h2>Task history</h2>
          {!jobs.length && <p>No sandbox tasks in this project yet.</p>}
          {jobs.map((job) => (
            <button
              key={job.id}
              className="sandbox-task quiet"
              aria-pressed={selected?.id === job.id}
              onClick={() =>
                void action(async () => {
                  setSelected(await api<SandboxJob>("/sandbox/jobs/" + job.id));
                  setArtifacts([]);
                  setReviewed(false);
                })
              }
            >
              <strong>{job.goal.slice(0, 100)}</strong>
              <span>
                {job.kind} · {job.status.replaceAll("_", " ")}
              </span>
              <small>{when(job.created_at)}</small>
            </button>
          ))}
        </section>
        <section
          aria-label="Sandbox task evidence"
          className="card"
          aria-live="polite"
        >
          <h2>Execution evidence</h2>
          {!selected ? (
            <p>Select a task to inspect its evidence.</p>
          ) : (
            <>
              <h3>{selected.goal}</h3>
              <p><small>Run ID: <code>{selected.id}</code></small></p>
              <p className="status">{selected.status.replaceAll("_", " ")}</p>
              {selected.status === "uncertain" && <p role="alert">The write outcome is uncertain. Do not repeat it. The operator must reconcile the target state before another attempt.</p>}
              {selected.error && (
                <p role="alert" className="error">
                  {selected.error}
                </p>
              )}
              {selected.plan && (
                <>
                  <p>{selected.plan.explanation}</p>
                  {selected.evidence?.url && (
                    <p>Observed URL: {selected.evidence.url}</p>
                  )}
                  <details open={selected.status === "waiting_approval"}>
                    <summary>Exact execution plan</summary>
                    <pre>
                      {selected.plan.code ??
                        JSON.stringify(selected.plan.steps, null, 2)}
                    </pre>
                  </details>
                </>
              )}
              {selected.evidence?.screenshot && (
                <figure>
                  <img
                    className="sandbox-screenshot"
                    alt="Captured sandbox browser page"
                    src={
                      "data:image/jpeg;base64," + selected.evidence.screenshot
                    }
                  />
                  <figcaption>
                    Screenshot SHA-256:{" "}
                    <code>{selected.evidence.screenshot_sha256}</code>
                  </figcaption>
                </figure>
              )}
              {selected.evidence?.verification && (
                <p>
                  Vultr verification:{" "}
                  {selected.evidence.verification.verified
                    ? "passed"
                    : "failed"}
                  . {selected.evidence.verification.explanation}
                </p>
              )}
              {selected.status !== "waiting_approval" && selected.approval_snapshot?.screenshot && <details>
                <summary>Original approval screenshot</summary>
                <img className="sandbox-screenshot" alt="Browser state presented for the original approval" src={"data:image/jpeg;base64," + selected.approval_snapshot.screenshot} />
                <pre>{JSON.stringify(selected.approval_snapshot.authorization, null, 2)}</pre>
              </details>}
              {selected.status === "waiting_approval" && (
                <fieldset>
                  <legend>Approve exact browser actions</legend>
                  <p>
                    Target: {selected.url}. Approval expires{" "}
                    {when(selected.approval_expires_at)}. Actions may submit
                    data or change this site. Cancellation cannot undo completed
                    effects.
                  </p>
                  <code className="sandbox-digest">
                    {selected.approval_digest}
                  </code>
                  {selected.approval_snapshot?.authorization ? <details open>
                    <summary>Exact authorized request</summary>
                    <dl className="sandbox-facts">
                      <dt>Method</dt><dd>{selected.approval_snapshot.authorization.method}</dd>
                      <dt>Target</dt><dd>{selected.approval_snapshot.authorization.url}</dd>
                      <dt>Operation</dt><dd>{selected.approval_snapshot.authorization.operation_id}</dd>
                    </dl>
                    <h4>Payload</h4><pre>{selected.approval_snapshot.authorization.body}</pre>
                    <h4>Headers</h4><pre>{JSON.stringify(selected.approval_snapshot.authorization.headers, null, 2)}</pre>
                  </details> : <p role="alert">Exact request evidence is unavailable. Approval is disabled; reload the task or ask the operator to investigate.</p>}
                  {!selected.evidence?.verification?.verified && <p role="alert">Verification has not passed. Approval is disabled.</p>}
                  <label>
                    <input
                      type="checkbox"
                      checked={reviewed}
                      onChange={(e) => setReviewed(e.target.checked)}
                    />{" "}
                    I reviewed every selector, payload, screenshot and target above.
                  </label>
                  <label>
                    Confirm account password
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </label>
                  <div className="toolbar">
                    <button
                      disabled={busy || !reviewed || !password || !selected.evidence?.verification?.verified || !selected.approval_snapshot?.authorization}
                      onClick={() => void decision(true)}
                    >
                      Approve exact plan
                    </button>
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => void decision(false)}
                    >
                      Deny
                    </button>
                  </div>
                </fieldset>
              )}
              {selected.receipt && Object.keys(selected.receipt).length > 0 && <dl className="sandbox-facts">
                <dt>Exit status</dt><dd>{selected.receipt.exit_code === undefined ? "Not recorded" : String(selected.receipt.exit_code)}</dd>
                <dt>Container cleanup</dt><dd>{selected.receipt.destroyed === true ? "Removal confirmed" : selected.receipt.destroyed === false ? "Removal failed — operator attention required" : "Not recorded"}</dd>
                <dt>Observed runtime</dt><dd>{String(selected.receipt.runtime ?? "Not recorded")}</dd>
                <dt>Execution time</dt><dd>{selected.receipt.duration_ms === undefined ? "Not recorded" : `${String(selected.receipt.duration_ms)} ms`}</dd>
              </dl>}
              {(selected.evidence?.stdout !== undefined || selected.evidence?.stderr !== undefined) && <details open>
                <summary>Actual process output</summary>
                <h4>stdout</h4><pre>{selected.evidence.stdout || "(empty)"}</pre>
                <h4>stderr</h4><pre>{selected.evidence.stderr || "(empty)"}</pre>
              </details>}
              {artifacts.length > 0 && <section className="sandbox-artifacts" aria-label="Permitted output artifacts">
                <h3>Output artifacts</h3>
                <ul>{artifacts.map((file) => <li key={file.id}>
                  <a href={"/api/sandbox/artifacts/" + encodeURIComponent(file.id)} download>{file.name}</a> · {file.size} bytes · {file.media_type}
                </li>)}</ul>
              </section>}
              {!!selected.calls?.length && <details open>
                <summary>Recorded inference calls</summary>
                <ul className="sandbox-call-list">{selected.calls.map((call) => <li key={call.id}>
                  <strong>{call.phase.replaceAll("_", " ")}</strong> · {call.provider} / {call.model}
                  <br />{call.latency_ms} ms · {call.tokens === null ? "Tokens unknown" : `${call.tokens} tokens`} · usage {call.usage_status}
                  {call.cost_usd !== null && <> · ${call.cost_usd}</>}
                </li>)}</ul>
              </details>}
              {!!selected.events?.length && (
                <ol className="sandbox-timeline">
                  {selected.events.map((event, i) => (
                    <li key={i}>{event.kind.replaceAll("_", " ")}{event.at ? ` · ${when(event.at)}` : ""}</li>
                  ))}
                </ol>
              )}
              {!!Object.keys(selected.receipt ?? {}).length && (
                <details>
                  <summary>Containment receipt</summary>
                  <pre>{JSON.stringify(selected.receipt, null, 2)}</pre>
                </details>
              )}
              <div className="toolbar">
                {(active.has(selected.status) ||
                  selected.status === "waiting_approval") && (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      void action(async () => {
                        setSelected(
                          await api<SandboxJob>(
                            "/sandbox/jobs/" + selected.id + "/cancel",
                            "POST",
                          ),
                        );
                        await refresh();
                      })
                    }
                  >
                    Cancel task
                  </button>
                )}
                <button
                  className="secondary"
                  onClick={() => {
                    const url = URL.createObjectURL(
                      new Blob([JSON.stringify(selected, null, 2)], {
                        type: "application/json",
                      }),
                    );
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `sandbox-${selected.id}.json`;
                    link.click();
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                  }}
                >
                  Export evidence
                </button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
