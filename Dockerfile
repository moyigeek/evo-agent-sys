FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install pyinstaller -q && \
    pyinstaller --onefile --name kernel base_os/os_kernel.py && \
    mv dist/kernel . && \
    pip uninstall pyinstaller -y -q && \
    rm -rf build/ dist/ kernel.spec && \
    chmod +x kernel && \
    rm -rf base_os/ && \
    mkdir -p staging_area history_versions && \
    chmod -R 755 .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./kernel"]
