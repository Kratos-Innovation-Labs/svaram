# Deploying Svaram

## What you need

- One Linux server (Ubuntu 24.04 tested), 4 CPU cores. Memory depends on the languages:
  about 3 GB for the rasa languages with translation, 8 GB for all twelve languages.
- A domain name pointing at the server, for HTTPS (Let's Encrypt).
- Internet access during installation, to download Python packages and models. None after.

## Layout

```
/opt/svaram/src                  this repository (read-only for the services)
/opt/svaram/<service>/venv       one Python environment per service
/opt/svaram/<service>/model      its model files, checked by SHA-256 at every start
/etc/svaram/<service>.env        settings (see deploy/env/*.env.sample)
/var/www/svaram                  the pages, built by tools/build_site.py, plus phrases/
```

Each service runs under its own system user with the hardened unit in `deploy/systemd/`: no write
access to the code, network limited to localhost, a memory cap, nothing written to disk.

## Install

```bash
sudo bash deploy/install.sh --languages te,hi --domain your.domain
```

The installer is being finalised for the first public release; until then, follow the samples in
`deploy/` by hand, in this order: create the users and folders, create each venv from its
`requirements.txt`, download the models listed in CREDITS.md into `/opt/svaram/<service>/model` and
record their SHA-256 in the `.env` files, install the units and the nginx site, start the services,
then build the pages and make the phrase audio:

```bash
python3 tools/build_site.py --out /var/www/svaram --check
python3 tools/make_phrases.py --out /var/www/svaram
```

## Your own site

Edit `web/site.yaml`: your domain, the languages to show and their order, the footer line, and
whether search engines may list the site. Rebuild the pages after any change to it or to a pack.

## Updating

Pull the new version into `/opt/svaram/src`, run `python3 tools/check_pack.py`, restart the
services one at a time (`systemctl restart svaram-api` and so on), and rebuild the pages.
