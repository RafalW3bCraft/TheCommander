import { useState } from "react";
import { api } from "./api";
import type { components } from "./api-schema";

export type Project = components["schemas"]["ProjectView"];
export function ProjectSelector({
  projects,
  selected,
  onSelect,
  onSaved,
}: {
  projects: Project[];
  selected: string;
  onSelect: (id: string) => void;
  onSaved: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<"create" | "rename" | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState<number | null>(null);
  const current = projects.find((p) => p.id === selected);
  return (
    <div className="project-context">
      <div className="toolbar">
        <label>
          Project
          <select
            aria-label="Project"
            value={selected}
            disabled={!projects.length || busy || !!editing}
            onChange={(e) => onSelect(e.target.value)}
          >
            {!projects.length && <option value="">Loading projects…</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
                {p.is_default ? " · default" : ""}
              </option>
            ))}
          </select>
        </label>
        <button
          className="secondary"
          disabled={busy || !!editing}
          onClick={() => {
            setName("");
            setError("");
            setEditing("create");
          }}
        >
          New project
        </button>
        <button
          className="quiet"
          disabled={!current || busy || !!editing}
          onClick={() => {
            setName(current!.name);
            setRevision(current!.revision);
            setError("");
            setEditing("rename");
          }}
        >
          Rename project
        </button>
      </div>
      {!editing && error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {editing && (
        <form
          className="project-editor"
          onSubmit={(e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            void (async () => {
              try {
                const project = await api<Project>(
                  editing === "create" ? "/projects" : `/projects/${selected}`,
                  editing === "create" ? "POST" : "PATCH",
                  editing === "create" ? { name } : { name, revision },
                );
                await onSaved();
                onSelect(project.id);
                setEditing(null);
              } catch (error) {
                setError(
                  error instanceof Error
                    ? error.message
                    : "Project could not be saved.",
                );
                // Keep the original revision on conflicts. Never silently retry stale edits.
              } finally {
                setBusy(false);
              }
            })();
          }}
        >
          <label>
            Project name
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={120}
              aria-describedby={error ? "project-error" : undefined}
            />
          </label>
          {error && (
            <p id="project-error" className="error" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button disabled={busy}>
              {editing === "create" ? "Create project" : "Save project name"}
            </button>
            <button
              type="button"
              className="quiet"
              disabled={busy}
              onClick={() => {
                setEditing(null);
                void onSaved().catch((error) =>
                  setError(
                    error instanceof Error
                      ? error.message
                      : "Projects could not be refreshed.",
                  ),
                );
              }}
            >
              Cancel project edit
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
