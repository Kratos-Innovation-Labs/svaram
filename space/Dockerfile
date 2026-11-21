# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
#
# The Svaram demo Space: the same five services as svaram.live, each in its own Python
# environment with the exact versions in deploy/requirements/, plus a Gradio page on port 7860.
# Models are not in the image: space/start.sh downloads and checks them when the Space starts.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libgomp1 libsndfile1 curl unzip \
 && rm -rf /var/lib/apt/lists/*

COPY deploy/requirements /tmp/req
RUN python -m venv /opt/venv/voice     && /opt/venv/voice/bin/pip install -r /tmp/req/rasa.lock
RUN python -m venv /opt/venv/voice-hi  && /opt/venv/voice-hi/bin/pip install -r /tmp/req/kokoro.lock
RUN python -m venv /opt/venv/translate && /opt/venv/translate/bin/pip install -r /tmp/req/translate.lock
RUN python -m venv /opt/venv/voice-itts && /opt/venv/voice-itts/bin/pip install -r /tmp/req/indictts.lock
RUN python -m venv /opt/venv/space     && /opt/venv/space/bin/pip install -r /tmp/req/space.lock

# Hugging Face runs Spaces as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user SVARAM_SRC=/home/user/app GRADIO_ANALYTICS_ENABLED=False HF_HUB_DISABLE_TELEMETRY=1
WORKDIR /home/user/app
COPY --chown=user . /home/user/app

EXPOSE 7860
CMD ["bash", "space/start.sh"]
