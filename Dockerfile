# Multi-stage build for ByenatOS
# Stage 1: Build Rust components
FROM rust:1.75-slim as rust-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust source code
COPY VirtualCore/ ./VirtualCore/
COPY Kernel/ ./Kernel/

# Build Rust components
WORKDIR /app/VirtualCore
RUN cargo build --release

WORKDIR /app/Kernel
RUN cargo build --release

# Stage 2: Build Python components
FROM python:3.11-slim as python-builder

WORKDIR /app

# Install system dependencies for Python
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy Python source code
COPY LocalAIProcessor/ ./LocalAIProcessor/
COPY PersonalizationEngine/ ./PersonalizationEngine/

# Install Python dependencies
WORKDIR /app/LocalAIProcessor
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/PersonalizationEngine
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: Runtime image
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    redis-server \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create byenatos user
RUN useradd -r -s /bin/false byenatos

# Set up directories
WORKDIR /opt/byenatos
RUN mkdir -p \
    /opt/byenatos/bin \
    /opt/byenatos/lib \
    /opt/byenatos/data \
    /opt/byenatos/logs \
    /opt/byenatos/config \
    && chown -R byenatos:byenatos /opt/byenatos

# Copy built Rust binaries
COPY --from=rust-builder /app/VirtualCore/target/release/virtual-core /opt/byenatos/bin/
COPY --from=rust-builder /app/Kernel/target/release/kernel /opt/byenatos/bin/

# Copy Python runtime
COPY --from=python-builder /usr/local /usr/local
COPY --from=python-builder /app/LocalAIProcessor /opt/byenatos/lib/ai-processor
COPY --from=python-builder /app/PersonalizationEngine /opt/byenatos/lib/personalization-engine

# Copy configuration files
COPY Config/ /opt/byenatos/config/
COPY Scripts/docker/ /opt/byenatos/scripts/

# Copy startup script
COPY Scripts/docker/entrypoint.sh /opt/byenatos/entrypoint.sh
RUN chmod +x /opt/byenatos/entrypoint.sh

# Create data volume
VOLUME ["/opt/byenatos/data"]

# Expose ports
EXPOSE 8080 8081 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER byenatos

# Set environment variables
ENV BYENATOS_DATA_DIR=/opt/byenatos/data
ENV BYENATOS_CONFIG_DIR=/opt/byenatos/config
ENV BYENATOS_LOG_LEVEL=info
ENV RUST_LOG=info

# Entry point
ENTRYPOINT ["/opt/byenatos/entrypoint.sh"]
CMD ["start"]

# Labels
LABEL maintainer="ByenatOS Team <dev@byenatos.org>"
LABEL version="0.1.0-alpha"
LABEL description="ByenatOS - AI时代的个人智能中间层"
LABEL org.opencontainers.image.source="https://github.com/byenatos/byenatos"
LABEL org.opencontainers.image.documentation="https://docs.byenatos.org"
LABEL org.opencontainers.image.licenses="MIT"