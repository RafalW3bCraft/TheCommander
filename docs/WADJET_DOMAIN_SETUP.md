# Connect wadjet.tech to the existing Vultr deployment

Target application: `https://wadjet.tech` on `207.246.82.5`.
Reserved controlled browser target: `https://fixture.wadjet.tech`.

## Completed hosting configuration — 2026-11-08

DNS is correct on all four authoritative nameservers for both hostnames. The
root application now has a trusted Let's Encrypt certificate and redirects HTTP
to HTTPS. The fixture hostname is reserved; no fixture service/write endpoint is
being published as part of this hosting change.

External probes connected to the public VM address with hostname/SNI and full
certificate verification: HTML, JavaScript/CSS and liveness/readiness returned
200; private account/project endpoints returned 401; a foreign-origin login
request returned 403. Ordinary-worker heartbeat is current. Some recursive/system
resolvers still cache the earlier missing record, so those clients may need time
before the hostname resolves normally. Existing-owner browser login remains a
manual acceptance check.

A real Caddy container restart retained the same certificate; readiness returned
200 afterward over TLS 1.3.

The deployed API/worker image was retained and pinned as
`sha256:fc51789b877d4938af91190c280f37eb2c64bf5e1af176f201abd10355bb5d66`.
Their effective production flag is true and origin is `https://wadjet.tech`.
Existing private `.env` and `.env.runtime` files were preserved byte-for-byte.

An isolated restore verified matching record counts, one original owner and
successful decryption of three encrypted connections. The temporary restore
database was removed. Protected backup on the VM:
`/root/TheCommander/.runtime/domain-https-20261108T103816Z`.
This backup contains private data and configuration; do not publish it.

### Actual restart command

The hostname lives in `.runtime/wadjet.env`; `.runtime/wadjet-image.yaml` pins the
existing API/worker image. Both files are on the VM, mode 0600. Use them on future
Compose invocations so the domain and pinned image remain effective:

```bash
cd /root/TheCommander
docker compose -p thecommander \
  --env-file .env --env-file .env.runtime --env-file .runtime/wadjet.env \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f compose.https.yaml \
  -f .runtime/wadjet-image.yaml config --quiet
docker compose -p thecommander \
  --env-file .env --env-file .env.runtime --env-file .runtime/wadjet.env \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f compose.https.yaml \
  -f .runtime/wadjet-image.yaml \
  up -d --no-build --no-deps --wait --wait-timeout 90 api worker proxy
curl --fail --show-error https://wadjet.tech/health/ready
```

The HTTPS Compose overlay supplies the process origin and production flag. A
future native sandbox runner still needs its own matching service environment;
this hosting change does not claim that runner or both workflows are verified.

### Actual rollback

To return to the previous private HTTP deployment, keep DNS, backups, database and
notes volumes. Stop the proxy and recreate API/worker using the original overlays
and retained image, without the HTTPS overlay:

```bash
cd /root/TheCommander
docker stop thecommander-proxy-1
docker compose -p thecommander --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f .runtime/wadjet-image.yaml \
  up -d --no-build --no-deps --wait --wait-timeout 90 api worker
curl --fail --show-error http://127.0.0.1:8000/health/ready
```

No original secret-file restoration is needed for this specific change because
those files were not edited. Rollback is documented, not executed against the
accepted HTTPS deployment. Never use `down -v` or erase certificate volumes.

## Historical starting observations — 2026-11-08

- Public authoritative DNS uses `ns1.dns.host` through `ns4.dns.host`.
- The root has no A/AAAA record; `fixture.wadjet.tech` does not resolve.
- The existing VM application is healthy at `127.0.0.1:8000`, with an initialized
  owner and a private database on `127.0.0.1:5434`.
- The existing Compose project is `thecommander`, in `/root/TheCommander`.
  Its checkout is on `vultr` and contains uncommitted work: preserve it.
- Ports 80/443 have no listener. UFW currently permits SSH only.

These are starting observations, not completed DNS/TLS proof.

## 1. Operator: add DNS at Get.tech

Sign in through https://get.tech/ and open the domain's DNS Service / Manage DNS
page. Keep the current nameservers and unrelated MX/TXT/verification records.

| Type | Host Name | Destination IPv4 address | TTL |
|---|---|---|---|
| A | Blank, meaning `wadjet.tech` | `207.246.82.5` | `14400`, or the panel default |
| A | `fixture` | `207.246.82.5` | `14400`, or the panel default |

If the panel uses `@` for the root, use `@` instead of blank. In a suffix-appending
Host Name field, do not enter the full domain. Add no AAAA record unless a working
VM IPv6 address and matching routing are independently verified. Do not use URL
forwarding. No web-hosting purchase or paid certificate is needed for this setup.

Official field instructions:
https://cp.get.tech/kb/servlet/KBServlet/faq471.html

## 2. Operator: independently verify the host and network rules

From Vultr's web console, run:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Expected fingerprint:
`SHA256:6GRp23B9wYYyLHCKyb421igSvTO00sHpL/KVIJiDP0M`.
Report an exact match before private configuration changes. Investigate any
mismatch; do not bypass SSH host checking.

If a Vultr Firewall group is attached, allow inbound TCP 80 and 443 for the web
service while preserving working SSH access. Keep database and Docker ports
private. Apply corresponding UFW rules during the coordinated deployment.

## 3. Engineering: verify DNS before HTTPS rollout

```bash
dig @ns1.dns.host wadjet.tech A +short
dig @1.1.1.1 wadjet.tech A +short
dig @8.8.8.8 wadjet.tech A +short
dig @1.1.1.1 fixture.wadjet.tech A +short
```

Expected IPv4 result: `207.246.82.5`. Check AAAA and CAA separately. Recursive
resolvers may temporarily cache the earlier absence of a record. Verify results
instead of assuming a fixed propagation delay.

## 4. Engineering: preserve configuration and enable the existing HTTPS overlay

Before changing the live stack, retain protected backups of its existing
configuration and database, record the running image IDs, and verify the local
application image still matches the running API/worker. Do not pull source,
rebuild dirty work, regenerate keys, delete volumes or initialize another owner.

For a future installation using the standard two-file configuration, use a local
editor on the VM to merge these intended assignments:

- `.env`: `APP_DOMAIN=wadjet.tech`
- `.env.runtime`: `APP_ORIGIN=https://wadjet.tech` and `PRODUCTION=true`

Keep every other value, especially encryption/bootstrap/database secrets. Keep
both files mode `0600`; do not print their contents. The HTTPS Compose overlay
also supplies the exact origin and production flag to API/worker processes.

The generic existing deployment check, after all prerequisites pass, is:

```bash
cd /root/TheCommander
docker compose --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f compose.https.yaml config --quiet
```

Pull only the already-pinned Caddy proxy image if absent. Recreate API/worker and
start the proxy with the same files and `up -d --no-build --no-deps api worker proxy`.
This uses the existing application image; inspect its identity before and after.
Do not use the general startup script, which omits the HTTPS overlay.

Caddy obtains and renews the certificate; retain its persistent data/config
volumes. The fixture hostname is reserved only: do not expose fixture writes
until their independent authority/approval tests pass.

## 5. Acceptance and recovery

From outside the VM, verify HTTP redirects to HTTPS, trusted TLS, the application
page and `/health/ready`. Test existing-owner login manually, Secure/HTTP-only
session cookies, CSRF rejection, worker readiness, persisted settings and restart.
The domain is ready only after those checks pass; DNS alone is insufficient.

If TLS fails, check authoritative DNS, unexpected IPv6, CAA, both firewall layers,
port conflicts and redacted Caddy diagnostics before retrying. Do not repeatedly
recreate containers or disable TLS verification.

If the origin change breaks login, restore the protected pre-change configuration
and recreate the affected services using the recorded previous image and original
Compose files. Preserve all database/notes/proxy volumes and existing secrets.
