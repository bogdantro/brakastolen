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
python manage.py seed_plots       # the 54 plots from the current website, with map outlines
python manage.py seed_blog        # news from the old site (placeholders as drafts)
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

## Deploy (Linux: nginx → gunicorn → Django, PostgreSQL)

1. `.env` on the server, from `.env.example`: `DEBUG=False`, a new `SECRET_KEY`, `ALLOWED_HOSTS`,
   `SITE_URL`, the `DB_*` values, and `EMAIL_*` + `INQUIRY_NOTIFY_EMAILS` so new inquiries are e-mailed.
   On a test domain also `ALLOW_INDEXING=False`. First days live: `SECURE_HSTS_SECONDS=3600`, later 1 year.
2. Install and prepare:

   ```bash
   git lfs pull                          # the photos are stored in Git LFS
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py check --deploy       # only "SECURE_HSTS_PRELOAD" may remain – on purpose
   ```

3. First time only:

   ```bash
   python manage.py seed_plots           # the 54 plots from the old site, with map outlines
   python manage.py seed_blog            # news from the old site, with their pictures in media/
   python manage.py createsuperuser      # tick "staff" – this is the dashboard login
   ```

4. Run `gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 3` under systemd, and restart it after every deploy.
5. nginx serves uploads itself (Django does not when `DEBUG=False`) and passes the rest on:

   ```nginx
   client_max_body_size 20m;
   location /media/ { alias /path/to/brakastolen/media/; expires 30d; }
   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   ```

   Redirect `brakastolen.no`, `xn--brakastlen-6cb.no` and plain `http://` to the address in `SITE_URL`.
   Static files (`/static/`) are served by WhiteNoise with content-hashed names and year-long caching.
6. Back up the PostgreSQL database and the `media/` folder (uploaded photos) – neither is in git.
