FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN mkdir -p staging_area history_versions && \
    chmod -R 755 .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "base_os/os_kernel.py"]
