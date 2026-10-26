# Throw-away image: copies a build context and fails if anything secret, local or generated got in.
# Run from the repo root:  docker build --no-cache --progress=plain -f deploy/check-context.Dockerfile backend
FROM busybox:1.37.0
COPY . /ctx
RUN cd /ctx && BAD=$(find . \( -name '.env' -o -name '.env.*' ! -name '.env.example' -o -name '*.pdf' -o -name '*.pem' \
      -o -name '.venv' -o -name 'node_modules' -o -name '.next' -o -name '__pycache__' -o -name '*.tsbuildinfo' \
      -o -name 'next-env.d.ts' -o -name '.pytest_cache' -o -name '.ruff_cache' \)) ; \
    if [ -n "$BAD" ]; then echo "NOT CLEAN:"; echo "$BAD"; exit 1; fi; \
    echo "CONTEXT CLEAN: $(find . -type f | wc -l) files"