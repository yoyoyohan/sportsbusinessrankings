# NJ HS Spread Ratings

Multi-sport high school ratings from the shared Rankings Drive folder.

**Drive is read-only.** This app only downloads copies into `sources/` and never writes back to Google Drive or the original workbooks.

Folder: https://drive.google.com/drive/folders/1jRwUeH8mRB6gH_Gm4Rjc2IdIlYSX_cHO

## Run locally

```bash
cd knottsbase
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python import_workbook.py
uvicorn app:app --reload --port 8000
```

Open http://127.0.0.1:8000/

Local mode uses `data/ratings.db` (SQLite) unless `DATABASE_URL` is set.

## Share with Render + Supabase

The live site on Render talks to a Postgres database on Supabase. You upload ratings once from your laptop; your coach opens the Render URL.

### 1. Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Project Settings → Database → **Connection string** → **URI**
3. Choose **Session pooler** (host like `aws-0-….pooler.supabase.com`, port **5432**)
4. Replace the password placeholder
5. Copy `.env.example` to `.env` and paste the URI as `DATABASE_URL`
6. Set `ADMIN_TOKEN` to a random string you will keep private

```bash
cp .env.example .env
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/migrate_to_supabase.py --yes
```

That copies your local `data/ratings.db` into Supabase (about 600k games; a minute or two).

### 2. GitHub

Render deploys from Git. From this folder:

```bash
git init
git add .
git commit -m "Ratings site for Render and Supabase"
```

Create an empty GitHub repo, then:

```bash
git remote add origin https://github.com/YOUR_USER/knottsbase.git
git branch -M main
git push -u origin main
```

Do not commit `.env` or `data/ratings.db`.

### 3. Render

1. [dashboard.render.com](https://dashboard.render.com) → New → Blueprint, or New → Web Service and point it at the GitHub repo
2. If it does not pick up `render.yaml`:
   - **Build:** `pip install -r backend/requirements.txt`
   - **Start:** `uvicorn app:app --host 0.0.0.0 --port $PORT --app-dir backend`
3. Environment variables:
   - `DATABASE_URL` — same Session pooler URI as in `.env`
   - `ADMIN_TOKEN` — same secret as in `.env`
4. Deploy. When it is live, send your coach `https://YOUR-SERVICE.onrender.com`

Free Render services sleep after inactivity; the first load can take ~30 seconds.

### 4. Auto-refresh from Drive (4× daily, free)

Uses **GitHub Actions** (not paid Render Cron):

1. Repo → **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DATABASE_URL`
3. Value: same Session pooler URI as on Render / in `.env`
4. Push is already set up; the workflow is `.github/workflows/refresh-rankings.yml`

It runs at **04:00, 10:00, 16:00, 22:00 UTC** (about 12am / 6am / noon / 6pm Eastern during EDT). You can also run it anytime under **Actions → Refresh rankings → Run workflow**.

Manual update still works: `/admin?token=YOUR_ADMIN_TOKEN`.

### 5. Manual laptop update

On your laptop, refresh from Drive (`/admin` on localhost), then:

```bash
python backend/migrate_to_supabase.py --yes
```

## Update locally

`/admin` → **Update from Drive** downloads copies (GET only) then rebuilds rankings.

Helpers and backups in Drive are ignored (`Ranking Post Helper`, `*_Backup`, `*_Helper`).
