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
