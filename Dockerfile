FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# System deps required by pandas/numpy/matplotlib stack when wheels are missing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libatlas-base-dev \
    libblas-dev \
    gfortran \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Create a non-root user
RUN useradd -m -u 1000 shiny
USER shiny

COPY --chown=shiny:shiny . .

EXPOSE 7860

CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "7860", "app.py"]
