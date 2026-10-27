# ITI-AI-Package: the ITI AI Platform package (step 9.5.7)

One folder that runs the whole platform with Docker: the API, the ITI AI Console, the game console, Postgres +
pgvector, Ollama, migrations, and a Caddy front door that is **off by default**.

## What is in it

| Path | What |
|---|---|
| `ITI-AI-Package-<tag>.tar` | all six images (`docker save`): iti-ai-api, iti-ai-console, iti-ai-game, pgvector, ollama, caddy |
| `deploy/docker-compose.yaml` | the stack (one file for every machine) |
| `deploy/.env.example` | the machine's settings: copy to `deploy/.env` |
| `deploy/Caddyfile`, `deploy/check-cert.ps1` | the front door and its certificate check (only with profile `door`) |
| `backend/.env.example` | the API's settings: copy to `backend/.env` and fill in |
| `data/uploads/` | uploaded documents (empty) |

No secrets, no documents, no models, no database. The models are pulled once into a volume; the database starts empty.

## Install (Windows PowerShell, from this folder)

1. Docker Desktop (with the NVIDIA GPU support for Ollama). Then load the images:
   `docker load -i ITI-AI-Package-<tag>.tar`
2. Settings: copy `deploy/.env.example` to `deploy/.env` and `backend/.env.example` to `backend/.env`; fill them in.
   Set `ITI_IMAGE_TAG=<tag>` in `deploy/.env`. A `$` in a `backend/.env` value must be inside single quotes.
3. Start: `docker compose -f deploy/docker-compose.yaml up -d --no-build`
   (never add `--remove-orphans`).
4. Models, once: `docker compose -f deploy/docker-compose.yaml exec ollama ollama pull qwen3.5:4b` and
   `... ollama pull bge-m3`.
5. Check: `docker compose -f deploy/docker-compose.yaml ps -a`: everything `healthy`, `migrate` `Exited (0)`.

## Something must face the network

Every service listens on 127.0.0.1 only. Users on other PCs need a front door with HTTPS:

- **Office laptop:** the native Caddy (`deploy/start-lan.ps1`), as today.
- **Cloud, option 1:** the provider's load balancer with its own certificate, pointing at the console and the API.
- **Cloud, option 2 or once the PCs trust our root:** `COMPOSE_PROFILES=model,door` in `deploy/.env`. With a public
  DNS name Caddy gets a public certificate by itself. With our internal root (`65A7AD4E…1594`), every user's PC must
  trust that root first (IT installs `root.crt`), or browsers refuse the site.

The certificate authority's private key (`root.key`) is never in this package.
