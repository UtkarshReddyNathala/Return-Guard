# Docker image for the worker (Python 3.13): the arq job runner with the LangGraph
# agent pipeline and the local CPU models (CLIP, the AI-image detector, scikit-learn).
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
  && rm -rf /var/lib/apt/lists/*

# Install the dependencies first, with an empty placeholder package, so changing the
# worker code does not repeat the ~15 minute PyTorch install. torch and torchvision
# must be a matching pair from the PyTorch CPU index, installed BEFORE .[ml].
# Otherwise pip installs a torchvision built for a different torch, and CLIP fails
# with "operator torchvision::nms does not exist".
COPY pyproject.toml ./
RUN mkdir -p pipeline && touch pipeline/__init__.py \
 && pip install --upgrade pip \
 && pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.13.0" torchvision \
 && pip install -e ".[ml]"

COPY . .
CMD ["arq", "pipeline.worker.WorkerSettings"]
