# Unofficial Fragrantica RSS

This repository creates two personal, unofficial RSS 2.0 feeds from public listing cards on [Fragrantica](https://www.fragrantica.com/):

- `docs/news.xml` — news, reviews, launches, columns, and events
- `docs/new-perfumes.xml` — newly listed perfume pages

Entries retain only feed metadata (title, URL, category, author/date where supplied, and a short page-provided description). They link to Fragrantica rather than republishing full articles.

## Automation

GitHub Actions runs `generate_feeds.py` every six hours and commits any changes. It can also be run from **Actions → Update RSS feeds → Run workflow**.

## RSS URLs

After the initial workflow has run, subscribe using:

- `https://raw.githubusercontent.com/mrs-baotus/fragrantica-rss/main/docs/news.xml`
- `https://raw.githubusercontent.com/mrs-baotus/fragrantica-rss/main/docs/new-perfumes.xml`

## Maintenance

Fragrantica can change its page layout. If a run fails, inspect the workflow log and adjust the extraction patterns in `generate_feeds.py`.
