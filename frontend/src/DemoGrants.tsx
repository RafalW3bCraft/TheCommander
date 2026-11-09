import { useState } from "react";
import { api, when } from "./api";
import type { Account } from "./AccountPage";

type Grant = {
  id: string;
  owner_id: string;
  expires_at: string;
  revoked_at: string | null;
  model: string;
  max_usd: number;
  max_tokens: number;
  max_runs: number;
};

export function DemoGrants({ accounts }: { accounts: Account[] }) {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function refresh() {
    setGrants(await api<Grant[]>("/admin/demo-grants"));
    setLoaded(true);
  }
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Judge access request failed");
    } finally {
      setBusy(false);
    }
  }
  const recipients = accounts.filter(
    (account) => account.role === "personal" && !account.disabled_at,
  );
  return (
    <section>
      <h3>Judge inference access</h3>
      <p>
        An expiring grant lets a judge use the operator’s validated Vultr
        connection without receiving its credential. Only accounts registered
        with a judge invitation qualify. Verify your operator password above
        first.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      <button
        className="secondary"
        disabled={busy}
        onClick={() => void action(refresh)}
      >
        Load judge grants
      </button>
      {loaded && !grants.length && <p>No judge grants issued.</p>}
      <ul className="account-list">
        {grants.map((grant) => (
          <li key={grant.id}>
            <div>
              <strong>
                {accounts.find((account) => account.owner_id === grant.owner_id)
                  ?.username || grant.owner_id}
              </strong>{" "}
              · {grant.model}
              <br />
              Expires {when(grant.expires_at)} · ceiling ${grant.max_usd},{" "}
              {grant.max_tokens.toLocaleString()} tokens, {grant.max_runs} runs
              <br />
              {grant.revoked_at
                ? "Revoked"
                : Date.parse(grant.expires_at) <= Date.now()
                  ? "Expired"
                  : "Active"}
            </div>
            {!grant.revoked_at && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    await api("/admin/demo-grants/" + grant.id, "DELETE");
                    await refresh();
                    setNotice(
                      "Judge grant revoked. Further provider dispatch is denied.",
                    );
                  })
                }
              >
                Revoke judge grant
              </button>
            )}
          </li>
        ))}
      </ul>
      <details>
        <summary>Create limited judge access</summary>
        <p>
          Enter reviewed prices for every permitted model, including the vision
          model when needed. Unknown prices or consumption prevent further
          calls. The aggregate pool is fixed when first created; later grants
          must use those same pool ceilings.
        </p>
        {!recipients.length && (
          <p>
            Load account access controls above after a judge has registered.
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            void action(async () => {
              let prices: unknown;
              try {
                prices = JSON.parse(String(data.get("prices")));
              } catch {
                throw new Error(
                  "Enter valid JSON for the reviewed model prices.",
                );
              }
              await api("/admin/demo-grants", "POST", {
                owner_id: String(data.get("owner_id")),
                model: String(data.get("model")).trim(),
                prices,
                expires_hours: Number(data.get("expires_hours")),
                max_usd: Number(data.get("max_usd")),
                max_tokens: Number(data.get("max_tokens")),
                max_runs: Number(data.get("max_runs")),
                aggregate_max_usd: Number(data.get("aggregate_max_usd")),
                aggregate_max_tokens: Number(data.get("aggregate_max_tokens")),
              });
              await refresh();
              setNotice(
                "Limited judge access created. The provider credential remains operator-owned.",
              );
            });
          }}
        >
          <label>
            Judge account
            <select name="owner_id" required defaultValue="">
              <option value="" disabled>
                Select a registered judge
              </option>
              {recipients.map((account) => (
                <option key={account.owner_id} value={account.owner_id}>
                  {account.username}
                </option>
              ))}
            </select>
          </label>
          <label>
            Validated Vultr model
            <input name="model" required maxLength={200} />
          </label>
          <label>
            Grant expiry in hours
            <input
              name="expires_hours"
              type="number"
              required
              min={1}
              max={168}
              defaultValue={24}
            />
          </label>
          <label>
            Reviewed model prices (USD per million tokens)
            <textarea
              name="prices"
              required
              rows={5}
              maxLength={4000}
              placeholder={
                '{"exact-model-id":{"input_usd_per_million":0.1,"output_usd_per_million":0.35}}'
              }
            />
          </label>
          <p className="muted">
            The placeholder demonstrates the format only. Enter authoritative
            prices for the exact models you verified.
          </p>
          <label>
            Judge dollar ceiling (USD)
            <input
              name="max_usd"
              type="number"
              min="0.000001"
              max={100}
              step="any"
              required
            />
          </label>
          <label>
            Judge token ceiling
            <input
              name="max_tokens"
              type="number"
              min={1}
              max={10000000}
              required
            />
          </label>
          <label>
            Judge run ceiling
            <input name="max_runs" type="number" min={1} max={100} required />
          </label>
          <label>
            Aggregate pool dollar ceiling (USD)
            <input
              name="aggregate_max_usd"
              type="number"
              min="0.000001"
              max={100}
              step="any"
              required
            />
          </label>
          <label>
            Aggregate pool token ceiling
            <input
              name="aggregate_max_tokens"
              type="number"
              min={1}
              max={10000000}
              required
            />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" required /> I verified the prices and
            authorize these judge and aggregate ceilings.
          </label>
          <button disabled={busy || !recipients.length}>
            Create limited judge grant
          </button>
        </form>
      </details>
    </section>
  );
}
