# ITI-AI-Package: the ITI AI Platform package (step 9.5.7)

One folder that runs the whole platform with Docker: the API, the ITI AI Console, the game console, Postgres +
pgvector, Ollama, migrations, and a Caddy front door that is **off by default**.
This file installs and starts it; `SETUP.md` continues with the admin account, documents, HR connections and API keys.

## What is in it

| Path | What |
|---|---|
| `ITI-AI-Package-<tag>.tar` | all six images (`docker save`): iti-ai-api, iti-ai-console, iti-ai-game, pgvector, ollama, caddy |
| `deploy/docker-compose.yaml` | the stack (one file for every machine) |
| `deploy/.env.example` | the machine's settings: copy to `deploy/.env` |
| `deploy/Caddyfile`, `deploy/check-cert.ps1` | the front door and its certificate check (only with profile `door`) |
| `backend/.env.example` | the API's settings: copy to `backend/.env` and fill in |
| `data/uploads/` | uploaded documents (empty) |
| `hrdotnet-sql/` | the 12 scripts that prepare an HRDotNet database for the HR answers, with their run order (`README.md`) |
| `SETUP.md` | after the install: admin account, documents, HR connections, API keys |

No secrets, no documents, no models, no database. The models are pulled once into a volume; the database starts empty.

## What the machine needs

- Windows 10/11 with Docker Desktop (WSL 2 backend), or Linux with Docker and the Compose plugin.
- About 20 GB free: the images unpack to about 12 GB, the two models about 4 GB.
- An NVIDIA GPU with a current driver (Linux: also the NVIDIA container toolkit). Without one, see "No NVIDIA GPU" below.
- Internet once, to pull the two models.

## Install (Windows PowerShell, from this folder)

1. Load the images: `docker load -i ITI-AI-Package-<tag>.tar` (six `Loaded image:` lines).
2. Settings: copy `deploy/.env.example` to `deploy/.env` and `backend/.env.example` to `backend/.env`. In `deploy/.env`
   set `ITI_PG_PASSWORD` (a new long password, no `$`) and `ITI_IMAGE_TAG=<tag>` (remove the `# ` in front); put the
   same password in `backend/.env`'s `ITI_DATABASE_URL`. A `$` in a `backend/.env` value must be inside single quotes.
3. Start: `docker compose -f deploy/docker-compose.yaml up -d --no-build`
   (never add `--remove-orphans`).
4. Models, once: `docker compose -f deploy/docker-compose.yaml exec ollama ollama pull qwen3.5:4b` and
   `... ollama pull bge-m3`.
5. Check: `docker compose -f deploy/docker-compose.yaml ps -a`: everything `healthy`, `migrate` `Exited (0)`.
6. The first Console account (the database starts empty; the Accounts page adds the others). The password is asked
   twice at a hidden prompt:
   `docker compose -f deploy/docker-compose.yaml exec api python -m scripts.create_console_user <name> --role super_admin`
   Then sign in at http://127.0.0.1:3000 on this machine.

## Check that it really answers

1. http://127.0.0.1:3000: the login page says "AI service connected"; sign in.
2. Overview: database, Ollama and both models green.
3. Documents: upload one text PDF to `iti-docs`; the job ends `done` with a chunk count.
4. Chat: a question from that PDF gets an answer citing its file and page; an off-topic question gets the polite
   "please ask HR" reply.
5. `docker compose -f deploy/docker-compose.yaml exec ollama ollama ps`: the model shows `100% GPU`.

HR record answers need the client company's HRDotNet database (an `.env` value set by the platform owner); without it
the platform answers document questions only.

## No NVIDIA GPU

The `ollama` container asks for the GPU and does not start without one. For a slow, CPU-only run, create
`deploy/cpu.yaml` with:

    services:
      ollama: { deploy: !reset {} }

and add `-f deploy/cpu.yaml` after the first `-f` in every compose command.

## Removing a test install

`docker compose -f deploy/docker-compose.yaml down -v` deletes this machine's containers, database and models.
Only on a test machine: never where the platform holds real data.

## Something must face the network

Every service listens on 127.0.0.1 only. Users on other PCs need a front door with HTTPS: either something this
machine already has (the provider's load balancer, an existing reverse proxy), or the Caddy container of this package.
**The certificate is set up on this machine.** The package brings none: no certificate authority, no keys.

### The Caddy container (profile `door`)

1. In `deploy/.env`: `COMPOSE_PROFILES=model,door`, this machine's addresses, and the certificate choice:

       ITI_CONSOLE_SITES=https://ai.example.local          # the console (testers: login and Chat only)
       ITI_API_SITES=https://ai.example.local:8443         # the API for the C# apps
       ITI_TLS=internal                                    # see the three choices below

   Several names: comma-separated. Left out, the names of the original laptop are used (wrong anywhere else).
2. `docker compose -f deploy/docker-compose.yaml up -d --no-build` starts it on 443 and 8443 of every address.
3. Open 443 (the users' PCs) and 8443 (the C# app servers only) in this machine's firewall.

| `ITI_TLS` | Certificate | What else to do |
|---|---|---|
| `internal` (default) | Caddy makes its **own** certificate authority on first start, kept in the `caddy-data` volume | Export its root: `docker compose -f deploy/docker-compose.yaml cp caddy:/data/caddy/pki/authorities/local/root.crt .` and have IT install `root.crt` in every user's PC under **Trusted Root Certification Authorities** (by policy). Back up the `caddy-data` volume: losing it makes a new root that every PC must trust again. Never copy `root.key` anywhere |
| `/certs/site.pem /certs/site.key` | The company's own certificate (e.g. from its internal CA) | Put the two files in `deploy/certs/` (mounted read-only; never commit or email the key). Renewal is the company's job |
| an email address, e.g. `it@example.com` | A **public** certificate (Let's Encrypt), renewed by Caddy | Only for a public DNS name that reaches this machine on 443. Nothing to install on the PCs |

Check from this machine (Windows), with its own name and root:
`powershell -NoProfile -ExecutionPolicy Bypass -File deploy\check-cert.ps1 -Port 443 -Name ai.example.local -RootFile .\root.crt`
→ `chains to that root: True`. Then, from a user's PC, `https://<name>/login` must open with no certificate warning:
a warning means that PC does not trust the root yet. Never let users click through a certificate warning.
