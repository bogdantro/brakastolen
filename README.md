# Brakastølen – nettside

Django website for Brakastølen (Tranberg Utvikling AS): hyttetomter og hytter på Vaset i Valdres.
Client research, page map and open questions: `CLIENT-BRIEF.md`.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # then set DEBUG=True and ALLOW_INDEXING=False in .env
python manage.py migrate
python manage.py seed_site        # plots, costs, FINN ad, zoning map and news from the old site
python manage.py createsuperuser  # tick "staff" – this is the dashboard login
python manage.py runserver
```

Site: http://127.0.0.1:8000/ · Dashboard: http://127.0.0.1:8000/dashboard/

## Checks

```bash
python manage.py test
python manage.py check --deploy   # with production values in .env
```

## Styles

SCSS is compiled next to each file and the `.css` is committed (no build step on the server):

```bash
sass --style=expanded static/scss/global/global.scss:static/scss/global/global.css   # etc.
```

## Images

`python manage.py optimize_images` shrinks new photos in `static/images/` (originals go to `originals/`).
Hero photos: drop files into `static/images/hero/` – they are picked up in name order.

## Deploy (Ubuntu: nginx → gunicorn → Django, SQLite)

The site runs on SQLite in production (fine for a site this size; switching to PostgreSQL later
is only `DB_*` in `.env` plus moving the data). Paths below assume `/srv/brakastolen` and a user
`brakastolen` – change them if your server is set up differently.

### 1. Server packages and folders

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv git git-lfs nginx certbot python3-certbot-nginx sqlite3
sudo adduser --system --group --home /srv/brakastolen brakastolen
sudo mkdir -p /srv/brakastolen/data /srv/brakastolen/backups
sudo chown -R brakastolen:brakastolen /srv/brakastolen
sudo -u brakastolen git clone https://github.com/bogdantro/brakastolen.git /srv/brakastolen/app
cd /srv/brakastolen/app
sudo -u brakastolen git lfs install --local && sudo -u brakastolen git lfs pull   # the photos
sudo -u brakastolen python3.12 -m venv .venv
sudo -u brakastolen .venv/bin/pip install -r requirements.txt
```

### 2. `.env` (in `/srv/brakastolen/app`, never in git)

Copy `.env.example` to `.env` and set at least:

```bash
DEBUG=False
SECRET_KEY=            # python3 -c "import secrets; print(secrets.token_urlsafe(64))"
ALLOWED_HOSTS=www.xn--brakastlen-6cb.no,xn--brakastlen-6cb.no,www.brakastolen.no,brakastolen.no
SITE_URL=https://www.xn--brakastlen-6cb.no
ALLOW_INDEXING=True    # False on a test domain
SQLITE_PATH=/srv/brakastolen/data/db.sqlite3
SECURE_HSTS_SECONDS=3600   # the first days live; raise to 31536000 when all is well
# So new inquiries are e-mailed (they are always saved in the dashboard either way):
EMAIL_HOST=            # e.g. smtp.domeneshop.no
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
INQUIRY_NOTIFY_EMAILS=post@brakastolen.no
```

`chmod 600 .env` so only the site's user can read it.

### 3. First time: database, files, content, login

```bash
cd /srv/brakastolen/app
sudo -u brakastolen .venv/bin/python manage.py migrate
sudo -u brakastolen .venv/bin/python manage.py collectstatic --noinput
sudo -u brakastolen .venv/bin/python manage.py seed_site           # plots, costs, FINN ad, zoning map, news
sudo -u brakastolen .venv/bin/python manage.py createsuperuser     # tick "staff" – the dashboard login
sudo -u brakastolen .venv/bin/python manage.py check --deploy      # only "SECURE_HSTS_PRELOAD" may remain
```

`seed_site` runs `seed_plots`, `seed_field_info` and `seed_blog`. Each only adds what is missing,
so running it again never overwrites what the client has changed in the dashboard.

### 4. gunicorn as a service – `/etc/systemd/system/brakastolen.service`

```ini
[Unit]
Description=Brakastølen (gunicorn)
After=network.target

[Service]
User=brakastolen
Group=brakastolen
WorkingDirectory=/srv/brakastolen/app
ExecStart=/srv/brakastolen/app/.venv/bin/gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now brakastolen
```

### 5. nginx – `/etc/nginx/sites-available/brakastolen`

```nginx
server {
    listen 80;
    server_name www.xn--brakastlen-6cb.no xn--brakastlen-6cb.no www.brakastolen.no brakastolen.no;
    client_max_body_size 20m;   # documents and photos uploaded in the dashboard

    # Uploads are served by nginx itself – Django doesn't when DEBUG=False
    location /media/ { alias /srv/brakastolen/app/media/; expires 30d; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/brakastolen /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d www.xn--brakastlen-6cb.no -d xn--brakastlen-6cb.no -d www.brakastolen.no -d brakastolen.no
```

Point the domains' DNS (A records) at the server before running certbot. Static files (`/static/`)
are served by WhiteNoise with content-hashed names and year-long caching – nothing to set up.

### 6. Every update

```bash
cd /srv/brakastolen/app
sudo -u brakastolen git pull && sudo -u brakastolen git lfs pull
sudo -u brakastolen .venv/bin/pip install -r requirements.txt
sudo -u brakastolen .venv/bin/python manage.py migrate
sudo -u brakastolen .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart brakastolen
```

### 7. Backups (the database and `media/` are not in git)

A nightly copy, kept for 30 days – `sudo crontab -u brakastolen -e`:

```cron
15 3 * * * sqlite3 /srv/brakastolen/data/db.sqlite3 ".backup '/srv/brakastolen/backups/db-$(date +\%F).sqlite3'" && tar -czf /srv/brakastolen/backups/media-$(date +\%F).tar.gz -C /srv/brakastolen/app media && find /srv/brakastolen/backups -mtime +30 -delete
```

`.backup` makes a consistent copy even while the site is running (a plain `cp` of a live SQLite
file can be broken). Copy the backups folder off the server now and then.
