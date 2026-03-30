# riscv-arch-test ACT4 build environment
# https://github.com/riscv/riscv-arch-test (branch: act4)
#
# Includes:
#   - riscv-gnu-toolchain  (GCC 15 / Binutils 2.44, built from source, statically linked)
#   - uv                   (Python project / venv manager)
#   - sail-riscv           (RISC-V reference model)
#   - podman               (required by ACT4 for riscv-unified-db)
#
# Usage:
#   docker build -t riscv-act4 .                                    # Native
#   docker build --platform linux/amd64,linux/arm64 -t riscv-act4 . # Cross-compilation
#   docker run -it --rm --privileged -v .:/mnt riscv-act4
#
#   Inside the container the repo root is at /mnt; run:
#     CONFIG_FILES=config/cores/<vendor>/<dut>/test_config.yaml make
#
#   Output files will be owned by root; fix ownership after building:
#     sudo chown -R $(id -u):$(id -g) work/
#
# Overridable build args (apply to all stages):
#   --build-arg RISCV_TOOLCHAIN_PREFIX=/opt/riscv
#   --build-arg SAIL_PREFIX=/opt/sail
#   --build-arg SAIL_VERSION=0.10

# Global ARGs - declared before any FROM so they are overridable across all stages.
# Each stage that uses them must re-declare them with a bare ARG (no default) to bring them into scope.
ARG RISCV_TOOLCHAIN_PREFIX=/opt/riscv
ARG SAIL_PREFIX=/opt/sail
ARG SAIL_VERSION=0.10

# Stage 1: build riscv-gnu-toolchain
#
# Always runs on the build machine ($BUILDPLATFORM) for speed.
# When BUILDARCH != TARGETARCH we install a build -> target cross-compiler and
# pass --host to configure so autotools compiles the toolchain executables
# (gcc, ld, objdump, …) for the target architecture. LDFLAGS=-static ensures
# no shared-lib dependencies survive into the final image, making the binaries
# safe to COPY across architectures.
FROM --platform=$BUILDPLATFORM ubuntu:24.04 AS toolchain-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG RISCV_TOOLCHAIN_PREFIX
ARG BUILDARCH
ARG TARGETARCH

ENV RISCV_TOOLCHAIN_PREFIX="${RISCV_TOOLCHAIN_PREFIX}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    autotools-dev \
    bc \
    bison \
    build-essential \
    cmake \
    ca-certificates \
    curl \
    flex \
    gawk \
    gperf \
    git \
    libexpat-dev \
    libglib2.0-dev \
    libgmp-dev \
    libmpc-dev \
    libmpfr-dev \
    libncurses-dev \
    libslirp-dev \
    libtool \
    ninja-build \
    patchutils \
    python3 \
    python3-tomli \
    texinfo \
    zlib1g-dev

# Install the build -> target cross-compiler when cross-compiling.
# We only need to cover the two directions: amd64↔arm64.
RUN if [ "${BUILDARCH}" != "${TARGETARCH}" ]; then \
      case "${TARGETARCH}" in \
        arm64) apt-get install -y --no-install-recommends \
                 gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
                 libc6-dev-arm64-cross ;; \
        amd64) apt-get install -y --no-install-recommends \
                 gcc-x86-64-linux-gnu g++-x86-64-linux-gnu \
                 libc6-dev-amd64-cross ;; \
        *) echo "Unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
      esac \
    fi \
 && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/riscv/riscv-gnu-toolchain /tmp/riscv-gnu-toolchain \
 && cd /tmp/riscv-gnu-toolchain \
 && sed -i 's/c,c++/c/g' Makefile.in \
 && sed -i 's/c,c++,fortran/c/g' Makefile.in \
 && if [ "${BUILDARCH}" != "${TARGETARCH}" ]; then \
      case "${TARGETARCH}" in \
        arm64) HOST_TRIPLE="aarch64-linux-gnu" ;; \
        amd64) HOST_TRIPLE="x86_64-linux-gnu"  ;; \
      esac; \
      CROSS_FLAGS="--host=${HOST_TRIPLE} CC=${HOST_TRIPLE}-gcc CXX=${HOST_TRIPLE}-g++"; \
    fi \
 && ./configure \
        --prefix="${RISCV_TOOLCHAIN_PREFIX}" \
        --disable-gdb \
        --disable-qemu \
        --disable-linux \
        --disable-nls \
        --enable-strip \
        ${CROSS_FLAGS} \
        --with-multilib-generator="\
rv32e-ilp32e--;\
rv32i-ilp32--;\
rv32im-ilp32--;\
rv32iac-ilp32--;\
rv32imac-ilp32--;\
rv32imafc-ilp32f--;\
rv32imafdc-ilp32d--;\
rv64i-lp64--;\
rv64ic-lp64--;\
rv64iac-lp64--;\
rv64imafdc-lp64d--;\
rv64im-lp64--;" \
 && GCC_EXTRA_CONFIGURE_FLAGS="\
--enable-languages=c \
--disable-gcov \
--disable-lto \
--disable-libgomp \
--disable-libssp \
--disable-libquadmath \
--disable-decimal-float \
--disable-libsanitizer \
--disable-libvtv \
--enable-static \
--disable-shared" \
    BINUTILS_TARGET_FLAGS_EXTRA="--disable-gprof --disable-gprofng" \
    LDFLAGS="-static -static-libgcc -static-libstdc++" \
    make -j"$(nproc)" \
 && rm -rf /tmp/riscv-gnu-toolchain

# Stage 2: fetch sail-riscv binary
FROM ubuntu:24.04 AS sail-fetcher

ARG DEBIAN_FRONTEND=noninteractive
ARG SAIL_VERSION
ARG SAIL_PREFIX

ENV SAIL_PREFIX="${SAIL_PREFIX}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN SAIL_OS="$(uname -s)" \
 && SAIL_ARCH="$(uname -m)" \
 && mkdir -p "${SAIL_PREFIX}" \
 && curl --location --fail \
      "https://github.com/riscv/sail-riscv/releases/download/${SAIL_VERSION}/sail-riscv-${SAIL_OS}-${SAIL_ARCH}.tar.gz" \
    | tar xz --directory="${SAIL_PREFIX}" --strip-components=1

# Stage 3: fetch uv binary
#
# The install script pulls a binary into ~/.local/bin
FROM ubuntu:24.04 AS uv-fetcher

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Stage 4: final runtime image
FROM ubuntu:24.04

LABEL description="RISC-V Architectural Certification Tests (ACT4) build env"
LABEL org.opencontainers.image.source="https://github.com/riscv/riscv-arch-test"

ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=UTC
ARG RISCV_TOOLCHAIN_PREFIX
ARG SAIL_PREFIX

# These must be ENV so the running container can find the binaries
ENV TZ="${TZ}"
ENV RISCV_TOOLCHAIN_PREFIX="${RISCV_TOOLCHAIN_PREFIX}"
ENV SAIL_PREFIX="${SAIL_PREFIX}"
ENV PATH="${RISCV_TOOLCHAIN_PREFIX}/bin:${SAIL_PREFIX}/bin:/root/.local/bin:${PATH}"
ENV CONTAINERS_CONF=/etc/containers/containers.conf
ENV CONTAINERS_STORAGE_CONF=/etc/containers/storage.conf

# Runtime deps only:
#   - python3: needed by uv-managed venvs and the ACT4 framework
#   - ca-certificates / make / git: needed to drive the ACT4 Makefile
#   - podman: required by ACT4 for riscv-unified-db
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    podman \
    python3 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=toolchain-builder "${RISCV_TOOLCHAIN_PREFIX}" "${RISCV_TOOLCHAIN_PREFIX}"
COPY --from=sail-fetcher      "${SAIL_PREFIX}"            "${SAIL_PREFIX}"
COPY --from=uv-fetcher        /root/.local                /root/.local

# Podman configuration for running inside Docker (--privileged).
#
#   storage.conf - vfs avoids stacking overlays on top of Docker's own overlay mount
#   containers.conf:
#     cgroup_manager = cgroupfs   don't try to delegate via systemd
#     events_logger  = file       journald unavailable inside Docker
#     no_pivot_root  = true       pivot_root blocked by Docker seccomp
#     cgroups        = disabled   don't create any cgroup for the container; eliminates the
#                                 conmon sandbox cgroup attempt that causes
#                                 "write cgroup.subtree_control: device or resource busy"
RUN cat > /etc/containers/storage.conf <<'EOF'
[storage]
driver = "vfs"
EOF

RUN cat > /etc/containers/containers.conf <<'EOF'
[engine]
cgroup_manager = "cgroupfs"
events_logger  = "file"
no_pivot_root  = true

[containers]
cgroups  = "disabled"
cgroupns = "host"
EOF

# Fix Git configuration so it doesn't complain about mixed permissions
RUN git config --global --add safe.directory /mnt \
 && git config --global --add safe.directory /mnt/external/riscv-unified-db

# Smoke-test: verify all the binaries landed correctly
RUN riscv64-unknown-elf-gcc --version \
 && sail_riscv_sim --version \
 && uv --version \
 && podman --version

WORKDIR /mnt

CMD ["/bin/bash"]
