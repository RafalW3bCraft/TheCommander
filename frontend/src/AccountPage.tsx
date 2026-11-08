import { useCallback, useEffect, useState } from "react";
import { api, setCSRF, when, type User } from "./api";
import type { components } from "./api-schema";

export type Account = {
  owner_id: string;
  username: string;
  display_name: string;
  role: "operator" | "personal";
  workspace_id: string;
  disabled_at: string | null;
  created_at: string;
};
type Session = components["schemas"]["SessionView"];
type Invitation = {
  id: string;
  purpose: "personal" | "judge";
  expires_at: string;
  consumed_at?: string | null;
  revoked_at?: string | null;
};

export function AccountPage({
  account,
  onAccount,
  onSession,
  onSignOut,
}: {
  account: Account | null;
  onAccount: (value: Account) => void;
  onSession: (value: User) => void;
  onSignOut: () => void;
}) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setSessions(await api<Session[]>("/auth/sessions"));
  }, []);
  const refreshAdmin = useCallback(async () => {
    const [people, invites] = await Promise.all([
      api<Account[]>("/admin/accounts"),
      api<Invitation[]>("/admin/invitations"),
    ]);
    setAccounts(people);
    setInvitations(invites);
  }, []);
  useEffect(() => {
    let current = true;
    void refresh().catch((e: Error) => current && setError(e.message));
    return () => {
      current = false;
    };
  }, [refresh]);
  async function action(fn: () => Promise<void>) {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Account request failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="account-workspace">
      <p>Your profile, password and signed-in sessions. Invitations create separate private accounts.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <p role="status" aria-live="polite">{notice}</p>
      <section>
        <h2>Personal profile</h2>
        {!account ? <button disabled={busy} onClick={() => void action(async () => {
          onAccount(await api<Account>("/account"));
        })}>Load account</button> : <>
          <p>Username: <strong>{account.username}</strong> · {account.role === "operator" ? "Operator" : "Personal account"}</p>
          <form key={account.owner_id + account.display_name} onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            void action(async () => {
              onAccount(await api<Account>("/account", "PATCH", { display_name: String(data.get("display_name")) }));
              setNotice("Profile saved.");
            });
          }}>
            <label>Display name<input name="display_name" defaultValue={account.display_name} maxLength={120} autoComplete="nickname" /></label>
            <button disabled={busy}>Save profile</button>
          </form>
        </>}
      </section>
      <section>
        <h2>Change password</h2>
        <p>Changing your password rotates this session and signs out your other sessions.</p>
        <form onSubmit={(e) => {
          e.preventDefault();
          const form = e.currentTarget;
          const data = new FormData(form);
          void action(async () => {
            const user = await api<User>("/account/password", "POST", {
              current_password: String(data.get("current_password")),
              password: String(data.get("password")),
            });
            setCSRF(user.csrf);
            onSession(user);
            form.reset();
            await refresh();
            setNotice("Password changed. Other sessions signed out.");
          });
        }}>
          <label>Current password<input name="current_password" type="password" required maxLength={256} autoComplete="current-password" /></label>
          <label>New password<input name="password" type="password" required minLength={12} maxLength={256} autoComplete="new-password" /></label>
          <button disabled={busy}>Change password and sign out other sessions</button>
        </form>
      </section>
      <section>
        <h2>Signed-in sessions</h2>
        {!sessions.length && <p>No session details loaded.</p>}
        <ul className="account-list">
          {sessions.map((session) => <li key={session.id}>
            <div><strong>{session.current ? "This session" : "Other session"}</strong><br />Started {when(session.created_at)}<br />Expires {when(session.expires_at)}</div>
            <button className="secondary" disabled={busy} aria-label={session.current ? "Sign out this session" : `Revoke session started ${when(session.created_at)}`} onClick={() => void action(async () => {
              await api("/auth/sessions/" + session.id, "DELETE");
              if (session.current) onSignOut();
              else { await refresh(); setNotice("Session revoked."); }
            })}>{session.current ? "Sign out this session" : "Revoke session"}</button>
          </li>)}
        </ul>
        <div className="actions">
          <button className="secondary" disabled={busy || sessions.filter((s) => !s.current).length === 0} onClick={() => void action(async () => {
            await api("/auth/sessions/revoke", "POST", { scope: "other" });
            await refresh();
            setNotice("Other sessions signed out.");
          })}>Sign out other sessions</button>
          <button className="secondary" disabled={busy} onClick={() => void action(async () => {
            await api("/auth/sessions/revoke", "POST", { scope: "all" });
            onSignOut();
          })}>Sign out all sessions</button>
        </div>
      </section>
      {account?.role === "operator" && <section>
        <h2>Invitations and account access</h2>
        <p>Verify your password to manage invitations and personal accounts. Judge invitations create personal accounts; provider access requires a separately configured grant.</p>
        <form onSubmit={(e) => {
          e.preventDefault();
          const form = e.currentTarget;
          const password = String(new FormData(form).get("password"));
          void action(async () => {
            await api("/auth/reauthenticate", "POST", { password });
            form.reset();
            await refreshAdmin();
            setNotice("Password verified. Account access details loaded.");
          });
        }}>
          <label>Verify operator password<input name="password" type="password" required autoComplete="current-password" maxLength={256} /></label>
          <button disabled={busy}>Verify password and load access controls</button>
        </form>
        <h3>Create one-time invitation</h3>
        <form onSubmit={(e) => {
          e.preventDefault();
          const data = new FormData(e.currentTarget);
          void action(async () => {
            setToken("");
            const created = await api<Invitation & { token: string }>("/admin/invitations", "POST", {
              purpose: String(data.get("purpose")), expires_hours: Number(data.get("expires_hours")),
            });
            setToken(created.token);
            await refreshAdmin();
            setNotice("Invitation created. Save the token now; it is shown once.");
          });
        }}>
          <label>Invitation purpose<select name="purpose"><option value="personal">Private personal account</option><option value="judge">Judge account</option></select></label>
          <label>Expires in hours<input name="expires_hours" type="number" min={1} max={168} defaultValue={24} required /></label>
          <button disabled={busy}>Create invitation</button>
        </form>
        {token && <div className="invitation-token">
          <label>One-time invitation token<input readOnly value={token} autoComplete="off" spellCheck={false} /></label>
          <p>Send this privately. The recipient chooses “Register with invitation” on the sign-in screen.</p>
          <button className="secondary" onClick={() => setToken("")}>Hide token</button>
        </div>}
        <h3>Issued invitations</h3>
        {!invitations.length && <p>No invitations loaded. Verify your password above to refresh.</p>}
        <ul className="account-list">{invitations.map((invite) => <li key={invite.id}>
          <div>{invite.purpose} · expires {when(invite.expires_at)}<br />{invite.consumed_at ? "Used" : invite.revoked_at ? "Revoked" : "Unused"}</div>
          {!invite.consumed_at && !invite.revoked_at && <button className="secondary" disabled={busy} onClick={() => void action(async () => {
            await api("/admin/invitations/" + invite.id, "DELETE");
            await refreshAdmin();
            setNotice("Invitation revoked.");
          })}>Revoke invitation</button>}
        </li>)}</ul>
        <h3>Personal accounts</h3>
        {!accounts.length && <p>No accounts loaded.</p>}
        {accounts.map((person) => <div className="account-person" key={person.owner_id}>
          <p><strong>{person.username}</strong> · {person.role} · {person.disabled_at ? "Disabled" : "Active"}</p>
          {person.role !== "operator" && !person.disabled_at && <form onSubmit={(e) => {
            e.preventDefault();
            void action(async () => {
              await api("/admin/accounts/" + person.owner_id + "/disable", "POST");
              await refreshAdmin();
              setNotice(`Account ${person.username} disabled. Sessions revoked and queued work cancelled.`);
            });
          }}>
            <label className="checkbox-label"><input type="checkbox" required /> Disable {person.username}, revoke access and cancel queued work.</label>
            <button className="secondary" disabled={busy}>Disable {person.username}</button>
          </form>}
        </div>)}
      </section>}
    </div>
  );
}
