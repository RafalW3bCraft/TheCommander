import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { components } from "./api-schema";

type Search = components["schemas"]["MemorySearchView"];
type IndexStatus = components["schemas"]["MemoryIndexStatusView"];
type Project = components["schemas"]["ProjectView"];

export function MemorySearch({ projects }: { projects: Project[] }) {
  const [status, setStatus] = useState<IndexStatus | null>(null);
  const [result, setResult] = useState<Search | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const version = useRef(0);
  useEffect(() => {
    let active = true;
    void api<IndexStatus>("/memory/index-status")
      .then((value) => {
        if (active) setStatus(value);
      })
      .catch(() => {
        if (active)
          setError("Memory index status unavailable. Retry the search.");
      });
    return () => {
      active = false;
      ++version.current;
    };
  }, []);
  return (
    <details>
      <summary>Find relevant memory</summary>
      <p>
        {status
          ? status.configured
            ? `${status.pending} index updates pending · ${status.failed} awaiting retry · ${status.truncated} records indexed from a bounded prefix`
            : "Semantic index is disabled. Search uses canonical words and phrases."
          : "Checking memory index…"}
      </p>
      <form
        onChange={() => {
          ++version.current;
          setResult(null);
          setBusy(false);
        }}
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const request = ++version.current;
          const query = String(form.get("query") || "").trim();
          if (!query) return;
          const project = String(form.get("scope") || "");
          setBusy(true);
          setError("");
          void Promise.all([
            api<Search>(
              "/memory/search?q=" +
                encodeURIComponent(query) +
                (project ? "&project_id=" + encodeURIComponent(project) : ""),
            ),
            api<IndexStatus>("/memory/index-status"),
          ])
            .then(([found, current]) => {
              if (request === version.current) {
                setResult(found);
                setStatus(current);
              }
            })
            .catch((failure: unknown) => {
              if (request === version.current)
                setError(
                  failure instanceof Error
                    ? failure.message
                    : "Memory search failed",
                );
            })
            .finally(() => {
              if (request === version.current) setBusy(false);
            });
        }}
      >
        <label>
          Recall scope
          <select name="scope">
            <option value="">Owner-wide only</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name} + owner-wide
              </option>
            ))}
          </select>
        </label>
        <label>
          Recall question
          <input
            name="query"
            required
            maxLength={2000}
            placeholder="What did I decide about retries?"
          />
        </label>
        <button disabled={busy}>
          {busy ? "Finding memory…" : "Find relevant records"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <div aria-live="polite">
          <p>
            {result.index_status === "degraded"
              ? "Semantic index unavailable; showing canonical lexical matches."
              : result.method === "hybrid"
                ? "Ranked using lexical and semantic matches, checked against current canonical records."
                : "Canonical lexical matches."}
          </p>
          {result.query_truncated && (
            <p>
              The search query was shortened to the embedding model’s token
              limit.
            </p>
          )}
          {result.records.length === 0 ? (
            <p>No relevant eligible records found.</p>
          ) : (
            <ul>
              {result.records.map((record) => (
                <li key={record.id}>
                  <strong>{record.key}</strong>: {record.content}
                  <br />
                  <small>
                    {record.source} · revision {record.revision}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      <small>
        Expired and deleted records are excluded. Search considers up to 500
        recent canonical candidates. The optional index embeds a bounded prefix;
        full original records remain editable below.
      </small>
    </details>
  );
}
