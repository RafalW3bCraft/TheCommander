import { useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { components } from "./api-schema";

type Settings = components["schemas"]["SettingsView"];
type System = components["schemas"]["SystemView"];
const fields = [
  ["max_steps", "Model steps", 1],
  ["max_run_seconds", "Run time limit (seconds)", 30],
  ["max_context_chars", "Context limit (characters)", 4000],
  ["max_output_tokens", "Response token limit", 128],
  ["max_daily_runs", "Daily run limit", 1],
  ["max_daily_tokens", "Daily token limit", 1000],
] as const;

export function SettingsPage({
  connections,
  openMemory,
}: {
  connections: ReactNode;
  openMemory: () => void;
}) {
  const [tab, setTab] = useState("Connections");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [system, setSystem] = useState<System | null>(null);
  const [provider, setProvider] = useState("nebius");
  const [models, setModels] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([api<Settings>("/settings"), api<System>("/system/status")])
      .then(([s, health]) => {
        if (active) {
          setSettings(s);
          setProvider(s.effective.inference_provider ?? "nebius");
          setSystem(health);
        }
      })
      .catch((e) => {
        if (active)
          setError(e instanceof Error ? e.message : "Unable to load settings");
      });
    return () => {
      active = false;
    };
  }, []);
  async function job(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="actions" role="group" aria-label="Settings sections">
        {["Connections", "Model and limits", "Data and privacy", "System"].map(
          (name) => (
            <button
              key={name}
              className={tab === name ? "" : "secondary"}
              aria-pressed={tab === name}
              onClick={() => {
                setTab(name);
                setError("");
                setNotice("");
              }}
            >
              {name}
            </button>
          ),
        )}
      </div>
      {error && (
        <div role="alert" className="error">
          {error}{" "}
          <button
            className="quiet"
            disabled={busy}
            onClick={() =>
              void job(async () => {
                const fresh = await api<Settings>("/settings");
                setSettings(fresh);
                setProvider(fresh.effective.inference_provider ?? "nebius");
                setSystem(await api<System>("/system/status"));
                setNotice("Settings reloaded. Review before saving.");
              })
            }
          >
            Reload settings
          </button>
        </div>
      )}
      {notice && <p role="status">{notice}</p>}
      {tab === "Connections" && connections}
      {tab === "Model and limits" &&
        (settings ? (
          <section>
            <h2>Model and limits</h2>
            <p>
              Choose Nebius/NVIDIA or an explicitly configured optional API
              provider. Model or endpoint changes perform a small live
              validation request before saving. Limits cannot exceed the
              operator ceilings shown below.
            </p>
            <label>
              Inference provider
              <select
                aria-label="Inference provider"
                value={provider}
                disabled={busy}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setModels([]);
                  setNotice("");
                }}
              >
                <option value="nebius">Nebius · NVIDIA (default)</option>
                <option value="openai">OpenAI API</option>
                <option value="anthropic">Anthropic API</option>
              </select>
            </label>
            <p>
              No automatic fallback. Optional providers need their own API
              credentials in Connections.
            </p>
            <button
              className="secondary"
              disabled={busy}
              onClick={() =>
                void job(async () => {
                  const result = await api<components["schemas"]["ModelsView"]>(
                    "/models?provider=" + provider,
                  );
                  setModels(result.models);
                  setNotice(
                    `${result.models.length} models available for ${provider}.`,
                  );
                })
              }
            >
              Discover available models
            </button>
            <form
              key={`${settings.revision}:${provider}`}
              onSubmit={(event) => {
                event.preventDefault();
                const data = new FormData(event.currentTarget);
                const changes: Record<string, string | number | null> = {
                  revision: settings.revision,
                  inference_provider: provider,
                  ...(provider === "nebius"
                    ? {
                        nebius_model: String(data.get("model")),
                        nebius_base_url: String(data.get("endpoint")),
                      }
                    : { provider_model: String(data.get("model")) }),
                  daily_spend_limit_usd: data.get("spend")
                    ? Number(data.get("spend"))
                    : null,
                };
                for (const [key] of fields)
                  changes[key] = Number(data.get(key));
                void job(async () => {
                  setSettings(
                    await api<Settings>("/settings", "PATCH", changes),
                  );
                  setNotice(
                    "Settings saved. New tasks use these settings; queued tasks retain their model and cannot exceed current limits.",
                  );
                });
              }}
            >
              <label>
                {provider === "nebius" ? "NVIDIA model" : "Provider model"}
                <input
                  name="model"
                  list="nebius-models"
                  defaultValue={
                    provider === "nebius"
                      ? (settings.effective.nebius_model ?? "")
                      : provider === settings.effective.inference_provider
                        ? (settings.effective.provider_model ?? "")
                        : ""
                  }
                  required
                  maxLength={200}
                  pattern={
                    provider === "nebius" ? "nvidia/[A-Za-z0-9_.-]+" : undefined
                  }
                />
              </label>
              <datalist id="nebius-models">
                {models.map((model) => (
                  <option key={model} value={model} />
                ))}
              </datalist>
              {provider === "nebius" && (
                <label>
                  Nebius endpoint
                  <select
                    name="endpoint"
                    defaultValue={
                      settings.effective.nebius_base_url ?? undefined
                    }
                  >
                    <option value="https://api.tokenfactory.nebius.com/v1">
                      Token Factory · default
                    </option>
                    <option value="https://api.tokenfactory.us-central1.nebius.com/v1">
                      Token Factory · US Central
                    </option>
                  </select>
                </label>
              )}
              <div className="settings-grid">
                {fields.map(([key, label, minimum]) => (
                  <label key={key}>
                    {label}
                    <input
                      name={key}
                      type="number"
                      min={minimum}
                      max={settings.ceilings[key] ?? undefined}
                      defaultValue={settings.effective[key] ?? undefined}
                      required
                    />
                    <small>Operator ceiling: {settings.ceilings[key]}</small>
                  </label>
                ))}
              </div>
              <label>
                Daily spending limit (USD, optional)
                <input
                  name="spend"
                  type="number"
                  min="0.01"
                  step="0.01"
                  max={settings.ceilings.daily_spend_limit_usd ?? undefined}
                  defaultValue={settings.effective.daily_spend_limit_usd ?? ""}
                />
                <small>
                  Enforcement requires operator-configured pricing. Unknown
                  costs remain unknown and block inference when a spending limit
                  is set.
                </small>
              </label>
              <button disabled={busy}>
                {busy ? "Validating and saving…" : "Save model and limits"}
              </button>
            </form>
          </section>
        ) : (
          <p role="status">Loading settings…</p>
        ))}
      {tab === "Data and privacy" && (
        <section>
          <h2>Your data and privacy</h2>
          <p>
            Memory, conversations, schedules, and receipts persist in your
            database. Selected context goes to the selected inference provider;
            research queries go to Tavily; approved issue content goes to
            GitHub.
          </p>
          <p>
            Correct, export, or delete preferences in Memory. Delete a
            conversation from Assistant. Deletion does not erase previous
            messages, saved notes, provider copies, or backups. This is not
            local-only processing or end-to-end encryption.
          </p>
          <button onClick={openMemory}>Manage memory</button>
        </section>
      )}
      {tab === "System" && (
        <section>
          <h2>System status</h2>
          {system ? (
            <>
              <dl>
                <dt>API</dt>
                <dd>{system.api}</dd>
                <dt>Database</dt>
                <dd>{system.database}</dd>
                <dt>Worker</dt>
                <dd>
                  {system.worker_online
                    ? "Online"
                    : "Offline — queued tasks will wait"}
                </dd>
                <dt>Deployment</dt>
                <dd>
                  {system.production
                    ? "Production HTTPS required"
                    : "Local development"}
                </dd>
              </dl>
              <h3>Operator configuration</h3>
              {Object.entries(system.configured).map(([name, configured]) => (
                <p key={name}>
                  {name}: {configured ? "configured" : "missing"}
                </p>
              ))}
              <p>
                Change infrastructure settings in the private server
                environment, then restart API and worker. Back up data and
                preserve the encryption key before changes. Never paste secrets
                into logs or support reports.
              </p>
              <p>Restart required for: {system.restart_required.join(", ")}.</p>
            </>
          ) : (
            <p role="status">Loading system status…</p>
          )}
          <button
            className="secondary"
            disabled={busy}
            onClick={() =>
              void job(async () =>
                setSystem(await api<System>("/system/status")),
              )
            }
          >
            Refresh system status
          </button>
        </section>
      )}
    </>
  );
}
