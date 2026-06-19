FROM python:3.12-slim

# Non-root agent user (UID 1000)
RUN useradd -r -u 1000 -g users agent

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh agent.py ./
RUN chmod +x entrypoint.sh

# Container starts as root so entrypoint can fix /output ownership,
# then agent.py drops to UID 1000 via os.setuid() before any work runs.
ENTRYPOINT ["/app/entrypoint.sh"]
