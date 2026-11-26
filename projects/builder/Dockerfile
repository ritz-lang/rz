# The Ritz builder image (AGAST #4822, epic #4783): ritz1_selfhosted, rz and
# the Ritz sources a package imports, on the smallest base that runs them.
#
# Build it with projects/builder/test.sh, which does the two passes below
# from a clean `git archive` of one commit and then tests the image.  The
# context is the repository root:
#
#   docker build -f projects/builder/Dockerfile --target bootstrap -t rz-builder-bootstrap .
#   docker build -f projects/builder/Dockerfile --build-arg RZ_COMMIT=<sha> \
#       --build-arg RITZ1_SHA256=<sha256 of the bootstrap's ritz1_selfhosted> -t rz-builder .
#
# The second pass needs the first's ritz1_selfhosted sha256 for the image's
# label; the runtime stage checks it against the binary it ships, so a label
# that does not match the binary fails the build.  BuildKit reuses the
# bootstrap stage's layers, so the second pass costs only the runtime stage.
#
# Stages:
#   toolchain  Debian + clang/lld/llvm 21 (CI's CLANG_VERSION) + binutils,
#              make and Python: everything that builds the compiler.
#   bootstrap  ritz0 -> ritz1 -> ritz1_selfhosted, the stage 2 == stage 3
#              check, then the runtime tree and the native tools staged.
#   runtime    the base image + Python's standard library + those two.
#              The default target, and the image.
#
# projects/builder/README.md has the survey behind every choice here.

# Debian 13 slim, pinned by digest: glibc, because ritz1_selfhosted and every
# hosted Ritz binary name /lib64/ld-linux-x86-64.so.2 as their interpreter
# and ritz1_selfhosted has DT_NEEDED libc.so.6 (README, "Base image").
ARG BASE=debian:trixie-slim@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0
ARG LLVM_MAJOR=21

FROM ${BASE} AS toolchain
ARG LLVM_MAJOR
ARG DEBIAN_FRONTEND=noninteractive
# apt.llvm.org's signing key, pinned by checksum.
ADD --checksum=sha256:8b2a587ffd672c4687e7581dad4b2f6c1bb2ad6b480cd9771ba2ff48e0b8c75d \
    https://apt.llvm.org/llvm-snapshot.gpg.key /etc/apt/trusted.gpg.d/apt.llvm.org.asc
RUN set -eu; \
    chmod 644 /etc/apt/trusted.gpg.d/apt.llvm.org.asc; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates; \
    echo "deb https://apt.llvm.org/trixie/ llvm-toolchain-trixie-${LLVM_MAJOR} main" \
        > /etc/apt/sources.list.d/llvm.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        "clang-${LLVM_MAJOR}" "lld-${LLVM_MAJOR}" "llvm-${LLVM_MAJOR}" \
        binutils make python3 python3-venv; \
    rm -rf /var/lib/apt/lists/*
# The pin CI applies (.github/actions/setup): the versioned bindir first on
# PATH, so bare `clang`, `ld.lld`, `lld-link` and `llvm-ar` are LLVM 21.
ENV PATH=/usr/lib/llvm-${LLVM_MAJOR}/bin:$PATH

FROM toolchain AS bootstrap
ARG LLVM_MAJOR
# ritz0, the first stage of the bootstrap, is Python on llvmlite; the lock is
# the version CI installs.  Only the bootstrap needs it: the image does not.
COPY projects/ritz/requirements.lock /tmp/requirements.lock
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -c /tmp/requirements.lock llvmlite
ENV PATH=/opt/venv/bin:$PATH \
    RITZ_CACHE_DIR=/tmp/ritz-cas
COPY . /src
WORKDIR /src
RUN make -C projects/ritz ritz1-bootstrap
RUN bash projects/builder/check_fixed_point.sh projects/ritz/ritz1
RUN python3 projects/builder/stage_tree.py /src /stage \
 && bash projects/builder/collect_toolchain.sh /toolchain \
        clang ld.lld lld-link llvm-ar as ld readelf objcopy ar \
 && { echo "ritz1_selfhosted $(sha256sum < /stage/projects/ritz/ritz1/build/ritz1_selfhosted | cut -d' ' -f1)"; \
      echo "clang $(clang --version | head -1)"; \
      echo "binutils $(ld --version | head -1)"; } > /stage/BUILDER_INFO \
 && cat /stage/BUILDER_INFO

FROM ${BASE} AS runtime
ARG LLVM_MAJOR
ARG RZ_COMMIT
ARG RITZ1_SHA256
ARG DEBIAN_FRONTEND=noninteractive
# python3-minimal alone lacks tomllib, shutil, tempfile and concurrent.futures,
# which rz imports; libpython3.13-stdlib is the rest of the standard library.
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-minimal libpython3.13-stdlib \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/log/apt /var/log/dpkg.log
COPY --from=bootstrap /toolchain/ /
COPY --from=bootstrap /stage/ /rz/
# The labels must name what ships: refuse a missing commit, and a ritz1 sha256
# that is not this binary's.
RUN set -eu; \
    test -n "${RZ_COMMIT}" || { echo "RZ_COMMIT build-arg is required" >&2; exit 1; }; \
    echo "${RITZ1_SHA256}  /rz/projects/ritz/ritz1/build/ritz1_selfhosted" | sha256sum -c -; \
    echo "rz ${RZ_COMMIT}" >> /rz/BUILDER_INFO
ENV PATH=/usr/lib/llvm-${LLVM_MAJOR}/bin:$PATH \
    RITZ_CACHE_DIR=/tmp/ritz-cas
WORKDIR /rz
LABEL org.opencontainers.image.title="rz-builder" \
      org.opencontainers.image.description="ritz1_selfhosted, rz and the Ritz sources a package imports" \
      org.opencontainers.image.source="https://github.com/ritz-lang/rz" \
      org.opencontainers.image.revision="${RZ_COMMIT}" \
      dev.ritz.rz.commit="${RZ_COMMIT}" \
      dev.ritz.ritz1-selfhosted.sha256="${RITZ1_SHA256}"
