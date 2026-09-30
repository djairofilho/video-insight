FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home minio \
    && mkdir /data \
    && chown minio:minio /data

COPY --chmod=0755 minio /usr/local/bin/minio

USER minio
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
