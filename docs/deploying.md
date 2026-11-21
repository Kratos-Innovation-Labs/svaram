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
git clone https://github.com/Kratos-Innovation-Labs/svaram.git
cd svaram
sudo bash deploy/install.sh                              # every language in web/site.yaml
sudo bash deploy/install.sh --languages te,hi            # only these (and only the voices they need)
sudo bash deploy/install.sh --domain svaram.example.org  # also write an nginx site for your domain
```

The installer:

1. checks memory and disk for the languages you chose, and stops before changing anything if they
   do not fit;
2. uses Python 3.12 (the system's, or a private copy in `/opt/svaram/python` if the system has
   another version);
3. creates one system user and one Python environment per service, with the exact package
   versions svaram.live runs (`deploy/requirements/*.lock`);
4. downloads only the models those languages need, from their publishers, and checks every file
   against `deploy/models.yaml`; the Indic-TTS checkpoints are slimmed to their weights, and the
   weights are proved unchanged. The translation model needs its terms accepted on Hugging Face:
   the installer asks once for a token, hidden, and never stores it;
5. writes `/etc/svaram/*.env` (existing files are kept), installs the systemd units and starts the
   services one by one;
6. builds the pages into `/var/www/svaram`, makes the phrase audio, and runs `tools/selftest.py`,
   which prints a pass or fail line for every language.

Running it again is safe: finished steps are checked and skipped. With `--domain`, get a
certificate (for example with certbot), link the site from `sites-enabled`, then `nginx -t` and
reload.

## Your own site

Edit `web/site.yaml`: your domain, the languages to show and their order, the footer line, and
whether search engines may list the site. Rebuild the pages after any change to it or to a pack.

## Updating

Pull the new version into `/opt/svaram/src`, run `python3 tools/check_pack.py`, restart the
services one at a time (`systemctl restart svaram-api` and so on), and rebuild the pages.
