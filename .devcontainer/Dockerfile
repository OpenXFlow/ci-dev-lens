FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y \
    curl git build-essential sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Pinnutá verzia uv pre reprodukovateľnosť
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_VERSION=0.5.0 UV_INSTALL_DIR=/usr/local/bin sh

ENV PATH="/root/.cargo/bin:/root/.local/bin:$PATH"

# Install Rust (Commented out for Phase 1 - Enable when src-rust is populated)
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

WORKDIR /workspace