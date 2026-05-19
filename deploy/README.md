# Deploying OpenKeepr on a Debian VPS

Tested on **Debian 12 (Bookworm)**. The instructions assume you've just
provisioned a fresh server, have root access, and your DNS A/AAAA records
already point at the box.

## TL;DR — one command

```bash
# As root, on the VPS
sudo bash scripts/install_vps.sh openkeepr.example.com you@example.com --copy-ssh-keys
```

That bootstraps everything (user, repo, venv, env, systemd, nginx,
Let's Encrypt, fail2ban) and prints the initial admin password at the end.
Skip `--copy-ssh-keys` if you'd rather set up SSH access for the new user
yourself.

After it finishes, log in at `https://openkeepr.example.com/`, enable 2FA
and rotate the admin password.

---

## What the install script does

| Step | What | Where |
|------|------|-------|
| 1 | Installs system packages (python, nginx, certbot, fail2ban, sudo, sqlite3) | `apt-get install …` |
| 2 | Creates a dedicated service user `openkeepr` with home `/home/openkeepr` and shell `/bin/bash` | `/etc/passwd` |
| 3 | Optionally copies `/root/.ssh/authorized_keys` → `/home/openkeepr/.ssh/authorized_keys` | with `--copy-ssh-keys` |
| 4 | Clones the repo into `/home/openkeepr/app` (owned by `openkeepr`) | `git clone` |
| 5 | Creates `.venv` and installs `requirements.txt` | as the `openkeepr` user |
| 6 | Generates a fresh `.env` with random secrets, production flags, your hostname & admin e-mail | `/home/openkeepr/app/.env` |
| 7 | Creates the SQLite schema and seeds the initial admin (password printed once in the log) | `instance/openkeepr.db` |
| 8 | Downloads the vendored front-end assets (Bootstrap, marked, DOMPurify, icons) | `app/static/vendor/` |
| 9 | Installs the systemd unit and enables it (autostart at boot) | `/etc/systemd/system/openkeepr.service` |
| 10 | Installs the sudoers rule that lets `openkeepr` manage its own service | `/etc/sudoers.d/openkeepr` |
| 11 | Installs the `openkeepr` helper at `/usr/local/bin/openkeepr` | wrapper around `systemctl` |
| 12 | Configures the nginx site and obtains a Let's Encrypt cert via certbot | `/etc/nginx/sites-enabled/openkeepr.conf` |
| 13 | Sets up a basic fail2ban jail against rate-limited nginx replies | `/etc/fail2ban/jail.d/openkeepr.local` |

---

## Manual setup (step by step)

If you'd rather understand each piece:

### 1. Service user

```bash
sudo useradd \
    --create-home --home-dir /home/openkeepr \
    --shell /bin/bash \
    --comment "OpenKeepr service account" \
    openkeepr

# Optional — let yourself SSH directly as openkeepr by re-using root's keys
sudo install -d -o openkeepr -g openkeepr -m 0700 /home/openkeepr/.ssh
sudo cp /root/.ssh/authorized_keys /home/openkeepr/.ssh/authorized_keys
sudo chown openkeepr:openkeepr /home/openkeepr/.ssh/authorized_keys
sudo chmod 0600 /home/openkeepr/.ssh/authorized_keys
```

### 2. Code, venv, requirements, env

```bash
sudo -u openkeepr git clone https://github.com/OWNER/openkeepr.git /home/openkeepr/app
sudo -u openkeepr python3 -m venv /home/openkeepr/app/.venv
sudo -u openkeepr /home/openkeepr/app/.venv/bin/pip install -r /home/openkeepr/app/requirements.txt

# Copy .env.example and generate three secrets
sudo -u openkeepr cp /home/openkeepr/app/.env.example /home/openkeepr/app/.env
for k in SECRET_KEY RECIPIENT_HASH_SECRET SERVER_ENCRYPTION_KEY; do
    val=$(python3 -c "import secrets;print(secrets.token_urlsafe(64))")
    sudo -u openkeepr sed -i "s|^${k}=.*|${k}=${val}|" /home/openkeepr/app/.env
done
# Then edit FLASK_ENV, DEBUG, BASE_URL, SESSION_COOKIE_SECURE, etc. for production.
```

### 3. First boot (creates the DB and prints the admin password)

```bash
sudo -u openkeepr bash -c 'cd /home/openkeepr/app && set -a && . .env && set +a && .venv/bin/python -c "from app import create_app; create_app()"'
sudo -u openkeepr /home/openkeepr/app/.venv/bin/python /home/openkeepr/app/scripts/fetch_assets.py
```

### 4. systemd unit + sudoers + helper

```bash
sudo install -m 0644 /home/openkeepr/app/deploy/openkeepr.service /etc/systemd/system/openkeepr.service
sudo systemctl daemon-reload
sudo systemctl enable --now openkeepr

sudo install -m 0440 /home/openkeepr/app/deploy/openkeepr.sudoers /etc/sudoers.d/openkeepr
sudo visudo -c

sudo install -m 0755 /home/openkeepr/app/deploy/openkeepr-ctl.sh /usr/local/bin/openkeepr
```

### 5. nginx + Let's Encrypt

```bash
sudo sed "s/openkeepr.example.com/YOUR-HOSTNAME/g" \
    /home/openkeepr/app/deploy/nginx.conf.example \
    | sudo tee /etc/nginx/sites-available/openkeepr.conf >/dev/null
sudo ln -s /etc/nginx/sites-available/openkeepr.conf /etc/nginx/sites-enabled/openkeepr.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR-HOSTNAME
```

---

## Day-to-day operations

Log in **as the `openkeepr` user** (or any user with sudo) and use the
included helper:

```bash
openkeepr status         # show systemd state and last log lines
openkeepr start          # start the service
openkeepr stop           # stop it
openkeepr restart        # restart it (e.g. after editing .env)
openkeepr reload         # graceful worker reload (SIGHUP)
openkeepr logs           # follow the journal in real time
openkeepr journal        # show the last 200 log lines
```

The helper just calls `sudo systemctl …` / `sudo journalctl …` under the
hood — the sudoers rule installed in `/etc/sudoers.d/openkeepr` whitelists
exactly these commands without a password prompt.

If you prefer raw systemctl, all of these also work (as root or via sudo):

```bash
sudo systemctl status   openkeepr
sudo systemctl restart  openkeepr
sudo journalctl -u openkeepr -f
```

Autostart at boot is enabled automatically (`systemctl enable`), so the
service comes back after every reboot.

---

## Updating to a new release

```bash
sudo -u openkeepr git -C /home/openkeepr/app pull
sudo -u openkeepr /home/openkeepr/app/.venv/bin/pip install -r /home/openkeepr/app/requirements.txt
openkeepr restart
```

Database schema upgrades (additive only) and translation `.po → .mo`
recompilation happen automatically on startup.

---

## Backups

The DB is a single file at `/home/openkeepr/app/instance/openkeepr.db`.
A nightly backup is a single line in cron:

```cron
17 3 * * * openkeepr sqlite3 /home/openkeepr/app/instance/openkeepr.db ".backup /home/openkeepr/backups/openkeepr-$(date +\%F).db"
```

Encrypt the backup before shipping off-host (e.g. with `age` or `gpg`).
