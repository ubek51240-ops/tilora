import multiprocessing
import os

# Production Gunicorn sozlamalari
bind = os.getenv("BIND", "0.0.0.0:8010")
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
keepalive = 120
timeout = 120
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

# Loglar
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
