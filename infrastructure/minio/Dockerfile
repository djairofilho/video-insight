FROM debian:bookworm-slim
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home minio \
    && mkdir /data && chown minio:minio /data
# Artefatos oficiais, com SHA-256 publicado no release do projeto.
RUN case "$TARGETARCH" in \
      amd64) checksum=7c5bd8512c6e966455b1d198209358b2d191c77a83ab377c4073281065fb855f ;; \
      arm64) checksum=5c83cd2cf151717ba0243f73e1c7802ff36e272b67144bdd7f1f7d684fd6f03d ;; \
      *) echo "Arquitetura não suportada: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl -fL --retry 3 --connect-timeout 20 \
      "https://github.com/minio/minio/releases/download/RELEASE.2025-09-07T16-13-09Z/minio.linux-${TARGETARCH}.RELEASE.2025-09-07T16-13-09Z" \
      -o /usr/local/bin/minio \
    && echo "$checksum  /usr/local/bin/minio" | sha256sum -c - \
    && chmod 755 /usr/local/bin/minio
USER minio
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
