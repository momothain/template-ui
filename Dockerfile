# Dockerfile
### Basics
##temp builder
FROM python:3.12.5 AS builder

# Set the working directory in the container
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \ 
    PYTHONDONTWRITEBYTECODE=1

# RUN apt-get update &&
#     apt-get install -y --no-install-recommends gcc
# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

ARG GITHUB_TOKEN
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps git+https://$GITHUB_TOKEN@github.com/instalily/instalily-platform.git -w /app/wheels && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# RUN pip install --upgrade pip
# RUN pip wheel --no-cache-dir --no-deps git+https://$GITHUB_TOKEN@github.com/instalily/instalily-platform.git -w /app/wheels
# RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


## final stage
FROM python:3.12.5
WORKDIR /app
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

RUN pip install --no-cache /wheels/*
COPY . .

### Datadog
COPY --from=datadog/serverless-init:1 /datadog-init /app/datadog-init
RUN chmod +x /app/datadog-init

## ENV
ENV DD_SITE=us5.datadoghq.com \
    DD_SERVICE=templ-api \
    DD_VERSION=1
#
ENV DD_TRACE_ENABLED=true \
    DD_TRACE_PROPAGATION_STYLE=datadog \
    DD_LOGS_ENABLED=true \
    DD_LOGS_INJECTION=true
#
ENV DD_APM_ENABLED=true \
    DD_APM_NON_LOCAL_TRAFFIC=true \
    DD_AGENT_HOST=127.0.0.1 \
    DD_TRACE_AGENT_PORT=8126

# OPTIONAL
ENV LOG_LEVEL=INFO \
    DD_LOG_LEVEL=ERROR \
    DEBUG=false \
    DD_TRACE_DEBUG=false \
    DD_RUNTIME_METRICS_ENABLED=false


### APP


### RUN
# TODO: ARG $PORT
EXPOSE 8080
EXPOSE 8126
ARG DD_API_KEY
ENV DD_API_KEY=$DD_API_KEY
ENTRYPOINT ["/app/datadog-init"]
ARG PORT
ENV PORT=$PORT
CMD ["sh", "-c", "ddtrace-run gunicorn --bind 0.0.0.0:$PORT --workers 3 --worker-class uvicorn.workers.UvicornWorker --threads 4 --timeout 120 --log-level ERROR src.app:app"]
# CMD ["ddtrace-run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "3", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "4", "--timeout", "120", "--log-level", "ERROR", "src.app:app"]
