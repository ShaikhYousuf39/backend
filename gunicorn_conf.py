"""
Gunicorn configuration for production deployments.
Adjust worker counts based on CPU and memory budget.
"""
import multiprocessing
import os


# Bind to the port provided by the platform (Render/Heroku) or default to 8000
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Use Uvicorn worker class for ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Sensible default: (2 x cores) + 1
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# Keep connections alive for reverse proxies / load balancers
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "15"))

# Graceful timeout; hard limit for stuck workers
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))

# Access log disabled by default; enable via env var
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")

# Limit request line/field to prevent abuse
limit_request_line = 4094
limit_request_fields = 100

# Forwarded IPs when behind a proxy
forwarded_allow_ips = "*"
