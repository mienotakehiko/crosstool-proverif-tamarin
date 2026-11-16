# syntax=docker/dockerfile:1
# Snapshot APT instructions from the historical recipe, shared by both variants.
ARG GHC_VERSION=9.6.7
ARG TAMARIN_REPOSITORY=https://github.com/tamarin-prover/tamarin-prover.git
ARG TAMARIN_REF=c293106913ccf7bb41f49b0dc555a8074e8ea88c

FROM debian:bookworm-slim AS tamarin-source
ARG TAMARIN_REPOSITORY
ARG TAMARIN_REF

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/tamarin
RUN git init . \
    && git remote add origin "${TAMARIN_REPOSITORY}" \
    && git fetch --depth 1 origin "${TAMARIN_REF}" \
    && git checkout --detach FETCH_HEAD \
    && git rev-parse HEAD > TAMARIN_COMMIT \
    && test "$(cat TAMARIN_COMMIT)" = "${TAMARIN_REF}"

FROM haskell:${GHC_VERSION} AS shared-build
# FIX-CCS26-BULLSEYE-20260830: Debian 11 LTS ended in 2026; use a fixed security snapshot.
RUN set -eux; \
    for src in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do \
      [ -f "$src" ] || continue; \
      sed -i -E 's@https?://(deb|security)\.debian\.org/debian-security@http://snapshot.debian.org/archive/debian-security/20260830T000000Z@g' "$src"; \
    done; \
    grep -Rq 'http://snapshot.debian.org/archive/debian-security/20260830T000000Z' /etc/apt/sources.list /etc/apt/sources.list.d; \
    printf '%s\n' 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99bullseye-snapshot


WORKDIR /opt/build

RUN apt-get update && apt-get install -y --no-install-recommends \
    libncurses-dev \
    zlib1g-dev \
    pkg-config \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Copy only the files and folders that Stack needs to determine and build the
# dependencies. The translation source is obtained from Tamarin rather than
# duplicated in this artifact.
COPY --from=tamarin-source /opt/tamarin/stack.yaml /opt/tamarin/tamarin-prover.cabal ./
COPY --from=tamarin-source /opt/tamarin/LICENSE ./
COPY --from=tamarin-source /opt/tamarin/lib/. ./lib/
COPY --from=tamarin-source /opt/tamarin/src ./src
COPY --from=tamarin-source /opt/tamarin/data ./data
COPY --from=tamarin-source /opt/tamarin/images ./images
COPY --from=tamarin-source /opt/tamarin/TAMARIN_COMMIT /build-evidence/source.commit
COPY compile-variant.sh /usr/local/bin/compile-variant
RUN sha256sum -- lib/export/src/Export/ProVerif/Rule.hs \
    | grep -F 'faa7042e95c3ffb45b033de161abd17b006e268b534e699e9ccbe8a784c30b56' \
    && stack build --system-ghc --dependencies-only \
    && ghc --version > /build-evidence/ghc-version.txt \
    && stack --version > /build-evidence/stack-version.txt \
    && dpkg-query -W > /build-evidence/dpkg-packages.txt

FROM shared-build AS baseline
RUN --network=none /bin/sh /usr/local/bin/compile-variant baseline

FROM shared-build AS candidate
# This COPY imposes build order without importing baseline build products.
COPY --from=baseline /build-evidence/baseline/Rule.hs.sha256 /tmp/baseline-built.txt
COPY Rule.candidate.hs /opt/build/lib/export/src/Export/ProVerif/Rule.hs
RUN --network=none /bin/sh /usr/local/bin/compile-variant candidate

FROM scratch AS outputs
COPY --from=shared-build /build-evidence/ /metadata/
COPY --from=baseline /build-evidence/baseline/ /baseline/
COPY --from=candidate /build-evidence/candidate/ /candidate/
