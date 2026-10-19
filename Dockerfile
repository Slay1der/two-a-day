FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home app
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY config ./config
COPY cv ./cv
RUN mkdir -p data docs && chown -R app:app /app
USER app

ENTRYPOINT ["twoaday", "--root", "/app"]
CMD ["run"]
