FROM python:3.12-slim

WORKDIR /app

COPY evo_agent_active/ evo_agent_active/
COPY kernel .

RUN mkdir -p staging_area history_versions && \
    chmod +x kernel && \
    chmod -R 755 .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./kernel"]
