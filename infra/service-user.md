# Run fbsurvivor as a dedicated service user

Today gunicorn runs as `dan`. That account owns the code and `.env`, and it can use `sudo`.
So any bug that lets someone run code inside the app gives them the whole server.

This runbook moves the app to an unprivileged `fbsurvivor` user. That user can read the
code and secrets but can't change them, can't use sudo, and is boxed in by systemd.

`dan` still deploys: rsync, `uv sync`, migrations and `sudo systemctl` all keep running
as `dan`. Only the long-running web process changes users.

## What changes

| | Before | After |
|---|---|---|
| Process user | `dan` (has sudo) | `fbsurvivor` (no shell, no home, no sudo) |
| Code in `/opt/fbsurvivor` | owned and writable by `dan` | owned by `dan`, **read-only** to group `fbsurvivor`, hidden from everyone else |
| `.env` | readable by `dan` | `dan:fbsurvivor`, mode `640` |
| Start command | zsh → `/usr/local/bin/run-wsgi-server-fbsurvivor` → `uv run` | `.venv/bin/gunicorn` straight from the unit |
| Sandboxing | none | `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, … |
| Crash recovery | none | `Restart=on-failure` |

## 0. Check where Python lives

uv usually installs Python under `dan`'s home directory, and `.venv/bin/python` is a
symlink into it. The service user can't (and shouldn't) read `/home/dan`, so check first:

```sh
readlink -f /opt/fbsurvivor/.venv/bin/python
```

If that path is under `/home/dan`, do step 2's "move Python" part. If it's under `/usr`, skip it.

## 1. Create the user

```sh
sudo useradd --system --user-group --no-create-home \
  --home-dir /nonexistent --shell /usr/sbin/nologin fbsurvivor

# So dan can hand files to the group when deploying.
sudo usermod -aG fbsurvivor dan
```

Log out and back in (or `newgrp fbsurvivor`) so `dan` picks up the new group.

## 2. Fix ownership and permissions

```sh
cd /opt/fbsurvivor

sudo chown -R dan:fbsurvivor /opt/fbsurvivor
# Group can read files and enter directories; others get nothing.
sudo chmod -R u+rwX,g+rX,g-w,o-rwx /opt/fbsurvivor
# setgid on directories: new files (rsync, uv sync) inherit group fbsurvivor.
sudo find /opt/fbsurvivor -type d -exec chmod g+s {} +

# Secrets: dan can edit, the service can only read.
sudo chown dan:fbsurvivor /opt/fbsurvivor/.env
sudo chmod 640 /opt/fbsurvivor/.env
```

**Move Python, if step 0 pointed into `/home/dan`:**

```sh
sudo install -d -o dan -g fbsurvivor -m 2750 /opt/uv-python
export UV_PYTHON_INSTALL_DIR=/opt/uv-python UV_LINK_MODE=copy
~/.cargo/bin/uv python install 3.14.10
rm -rf /opt/fbsurvivor/.venv
cd /opt/fbsurvivor && ~/.cargo/bin/uv sync --no-dev
readlink -f .venv/bin/python   # should now be under /opt/uv-python
```

`UV_LINK_MODE=copy` matters. By default uv hardlinks packages from `~/.cache/uv`, so the
venv files would share permissions with `dan`'s cache instead of getting the
`fbsurvivor` group.

## 3. Check it works as the service user, before switching

```sh
cd /opt/fbsurvivor
sudo -u fbsurvivor env DJANGO_SETTINGS_MODULE=fbsurvivor.settings \
  .venv/bin/python manage.py check --deploy

# Should fail with "Permission denied": the app must not be able to change its own code.
sudo -u fbsurvivor touch /opt/fbsurvivor/manage.py
```

If `check` fails with a permission error, fix it before going on. The site is still
running as `dan`, so nothing is down yet.

## 4. Replace the systemd unit

`/etc/systemd/system/wsgi-server-fbsurvivor.service`:

```ini
[Unit]
Description=fbsurvivor wsgi
After=network.target postgresql.service

[Service]
User=fbsurvivor
Group=fbsurvivor
WorkingDirectory=/opt/fbsurvivor
Environment=DJANGO_SETTINGS_MODULE=fbsurvivor.settings
# The code is read-only to this user, so don't try to write .pyc files.
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/opt/fbsurvivor/.venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 fbsurvivor.wsgi
Restart=on-failure
UMask=0027

# Sandboxing
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
ProtectProc=invisible
RestrictSUIDSGID=yes
RestrictNamespaces=yes
RestrictRealtime=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
CapabilityBoundingSet=
SystemCallArchitectures=native

[Install]
WantedBy=multi-user.target
```

Notes:

- `ProtectHome=yes` hides `/home` from the app, which is why Python can't live there.
- `ProtectSystem=strict` makes the whole filesystem read-only except `/tmp` (private
  to this service, thanks to `PrivateTmp`). The app writes only to Postgres, SMTP and
  stdout, so it needs nothing else. Gunicorn's worker heartbeat files go in `/tmp`.
- `--bind 127.0.0.1:8000` is gunicorn's default. Spelling it out means a future default
  change can't expose it publicly.
- Startup logging moves from `systemd-cat` to journald itself: `journalctl -u wsgi-server-fbsurvivor`.

Switch over:

```sh
sudo systemctl daemon-reload
sudo systemctl restart wsgi-server-fbsurvivor.service
sudo rm /usr/local/bin/run-wsgi-server-fbsurvivor
```

## 5. Verify

```sh
systemctl status wsgi-server-fbsurvivor.service
ps -o user=,cmd= -C gunicorn            # every line should say fbsurvivor
curl -sI https://fbsurvivor.com | head -1
systemd-analyze security wsgi-server-fbsurvivor.service   # aim for "OK" or better
```

Then log in on the site and load the board to check that the database and email work.

## 6. Repo changes, so the next deploy doesn't undo this

- **`infra/wsgi-server-fbsurvivor.service`**: replace it with the unit above.
- **`infra/run-wsgi-server-fbsurvivor`**: delete it.
- **`justfile` `deploy` rsync**: `rsync -a --no-group -e "$RSH" ...`. The flag must come
  before `-e`, not between `-e` and `"$RSH"`. Without it, `-a` copies your Mac's group
  (`staff`) onto the server. Don't use `--chmod` for the modes: macOS's built-in rsync
  (openrsync) accepts it but doesn't apply it.
- **`infra/deploy`**: near the top, add
  ```sh
  umask 027
  export UV_PYTHON_INSTALL_DIR=/opt/uv-python UV_LINK_MODE=copy
  ```
  This keeps files from `uv sync` group-readable but not world-readable, and keeps
  Python out of `/home`. After `cd /opt/fbsurvivor`, reset the modes on what rsync
  pushed (`chgrp -R fbsurvivor`, `chmod -R u+rwX,g+rX,g-w,o-rwx`, `g+s` on directories).
  Run `collectstatic` inside `(umask 022; ...)`, because nginx has to read
  `/srv/www/fbsurvivor/static`.

## 7. Optional follow-ups

- **Cron jobs** (`fbsurvivor/bin/send-reminders`, `cache-current-board`) can keep
  running as `dan`, but they run app code too. To move them, use
  `sudo crontab -u fbsurvivor -e`, or turn them into systemd timers with the same
  `User=` and sandbox settings.
- **Narrow `dan`'s sudo.** The deploy only needs
  `systemctl stop|start wsgi-server-fbsurvivor.service`. Restrict that in
  `/etc/sudoers.d/` only if you have another way to get root (a console, or another
  admin account). Otherwise you can lock yourself out.

## Rollback

Put the old unit back (`User=dan`,
`ExecStart=/usr/bin/zsh /usr/local/bin/run-wsgi-server-fbsurvivor`; the script is in git
history), then:

```sh
sudo systemctl daemon-reload && sudo systemctl restart wsgi-server-fbsurvivor.service
```

The permission changes don't need undoing, because `dan` still owns everything.
