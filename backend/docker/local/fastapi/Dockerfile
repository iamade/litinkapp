ARG PYTHON_VERSION=3.13.1

FROM python:${PYTHON_VERSION}-slim-bookworm AS python

#Stage 1: build dependency wheels
FROM python AS python-build-stage

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install \
    --no-install-recommends -y \
    build-essential \
    gcc \
    g++

# Copy requirements and install Python dependencies
COPY ./requirements.txt .

RUN pip wheel --wheel-dir /usr/src/app/wheels \
    -r requirements.txt \
    --no-cache-dir


# Stage 2: Python run stage
FROM python AS python-run-stage

ARG APP_HOME=/backend
ARG APP_USER=fastapi
ARG APP_GROUP=fastapi

# Install debugpy only for development
ARG ENVIRONMENT=production


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}



RUN apt-get update && apt-get install --no-install-recommends -y \
    sudo git bash-completion nano ssh \
    gettext \
    gcc \
    g++ \
    ffmpeg \
    tesseract-ocr \
    tesseract-ocr-eng \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r ${APP_GROUP} && \
    useradd -r -g ${APP_GROUP} -d ${APP_HOME} -m ${APP_USER}

RUN mkdir -p ${APP_HOME}/app/logs && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}/app/logs && \
    chmod 775 ${APP_HOME}/app/logs

COPY --from=python-build-stage /usr/src/app/wheels /wheels/

RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/

# Install debugpy only for development
RUN if [ "$ENVIRONMENT" = "development" ] ; then pip install debugpy ; fi

COPY --chown=${APP_USER}:{APP_GROUP} ./docker/local/fastapi/entrypoint.sh /entrypoint.sh
COPY --chown=${APP_USER}:{APP_GROUP} ./docker/local/fastapi/start.sh /start.sh
COPY --chown=${APP_USER}:{APP_GROUP} ./docker/local/fastapi/celery/worker/start.sh /start-celeryworker.sh
COPY --chown=${APP_USER}:{APP_GROUP} ./docker/local/fastapi/celery/beat/start.sh /start-celerybeat.sh
COPY --chown=${APP_USER}:{APP_GROUP} ./docker/local/fastapi/celery/flower/start.sh /start-flower.sh


RUN sed -i 's/\r$//g' /entrypoint.sh /start.sh /start-celeryworker.sh /start-celerybeat.sh /start-flower.sh && \
    chmod +x /entrypoint.sh /start.sh /start-celeryworker.sh /start-celerybeat.sh /start-flower.sh

#set ownership of the files
COPY --chown=${APP_USER}:${APP_GROUP} . ${APP_HOME}

# Expose debug port
EXPOSE 8000 5678

#set user to run the container
USER ${APP_USER}

ENTRYPOINT [ "/entrypoint.sh" ]