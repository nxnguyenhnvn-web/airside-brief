# Airside Brief

An aviation dashboard website: air-transport news, macro indicators and airport projects with live satellite imagery.

- **News** updates itself twice a day (06:30 and 12:30 Vietnam time) from aviation RSS feeds.
- **Macro figures** and **airport projects** are edited by hand in two small data files.
- Hosting is free on **GitHub Pages**. There is no server or database.

## Files

| Path | What it is |
|---|---|
| `index.html` | The whole website (layout, styling, charts, maps) |
| `data/news.json` | News stories. Written automatically by the updater |
| `data/macro.json` | Headline numbers, regional traffic chart, IATA outlook. Edit by hand |
| `data/projects.json` | Airport projects, coordinates and milestones. Edit by hand |
| `scripts/update_news.py` | Reads the feeds and updates `data/news.json` (Python, no extra packages) |
| `scripts/feeds.json` | The list of news feeds. Add or remove sources here |
| `.github/workflows/update-and-deploy.yml` | Runs the updater on a schedule and publishes the site |

## Put it online (about 10 minutes)

1. Create a free account at [github.com](https://github.com) if you don't have one.
2. Click **New repository**. Name it, for example, `airside-brief`. Choose **Public** (GitHub Pages is free for public repositories). Create it.
3. On the new repository page, click **uploading an existing file**. Drag in **everything inside this folder**, including the hidden `.github` folder. Click **Commit changes**.
   - On a Mac, press `Cmd + Shift + .` in Finder to show the hidden `.github` folder. On Windows, enable *View → Hidden items*.
   - If the `.github` folder won't upload by drag and drop, create the file by hand: **Add file → Create new file**, type the name `.github/workflows/update-and-deploy.yml`, and paste in the contents of that file.
4. Go to **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
5. Go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and save.
6. Go to the **Actions** tab, click **Update news and deploy**, then **Run workflow**. After a minute or two it turns green.
7. Your site is live at `https://YOUR-USERNAME.github.io/airside-brief/`. The link is also shown under **Settings → Pages**.

From then on the news refreshes by itself. You can press **Run workflow** any time to refresh immediately.

## Keep the macro numbers and projects current

Open `data/macro.json` or `data/projects.json` on GitHub, click the pencil icon, change the values and commit. The site republishes automatically.

Good sources for monthly updates:
- IATA press releases (passenger and cargo demand, around the end of each month): https://www.iata.org/en/pressroom/
- Airbus and Boeing monthly orders and deliveries
- Vietnam: Civil Aviation Authority of Vietnam (CAAV) and ACV announcements

**Adding an airport project:** copy one entry in `data/projects.json` and change it. `lat` and `lng` are the site coordinates; right-click the spot in Google Maps to copy them. `zoom` is 13 for a wide view or 14 for a closer one. `status` is one of `operating`, `opening`, `construction`, `planning`. `milestone.date` drives the countdown; add `"label"` (e.g. `"2029"`) when only a year is known.

## Change the news sources

Edit `scripts/feeds.json`. Each feed needs a `name`, a `url` (any RSS or Atom feed) and a fallback `cat`. Add `"vn": true` to mark every story from that feed as Vietnam news. Google News search feeds work well for any topic:

```
https://news.google.com/rss/search?q=YOUR+SEARCH+WORDS+when:2d&hl=en-US&gl=US&ceid=US:en
```

For Vietnamese-language results use `&hl=vi&gl=VN&ceid=VN:vi`.

Categories are chosen by keyword rules at the top of `scripts/update_news.py` (`RULES`). Stories older than 30 days are dropped, and at most 150 are kept.

## Run it on your own computer

The page loads its data files, so it needs a small local web server rather than a double-click:

```bash
cd airside-brief
python3 scripts/update_news.py     # optional: fetch fresh news now
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Satellite imagery

Each project card shows Esri World Imagery (Maxar, Earthstar Geographics) through Leaflet. The links on each card open:
- **Google satellite**: the same spot in Google Maps
- **Sentinel-2 (recent)**: Copernicus Browser, with passes every few days, good for watching construction progress
- **Esri Wayback**: older imagery releases to compare before and after
- **NASA Worldview**: daily low-resolution imagery

Esri's imagery tiles are free for non-commercial use with attribution. If you plan to use the site commercially, check Esri's terms or switch to another imagery provider in `index.html` (search for `World_Imagery`).
