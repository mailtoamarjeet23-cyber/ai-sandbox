FROM python:3.12-slim

# su-exec: lightweight privilege-drop helper (replaces gosu, no external deps)
RUN apt-get update \
 && apt-get install -y --no-install-recommends su-exec \
 && rm -rf /var/lib/apt/lists/*

# Non-root agent user (UID 1000)
RUN useradd -r -u 1000 -g users agent

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh agent.py ./
RUN chmod +x entrypoint.sh

# Container starts as root so entrypoint can fix /output ownership,
# then su-exec drops to UID 1000 before python runs.
ENTRYPOINT ["/app/entrypoint.sh"]
