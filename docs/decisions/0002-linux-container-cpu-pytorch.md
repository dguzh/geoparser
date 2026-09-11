# ADR 0002: CPU-only PyTorch in Linux containers

## Status

Accepted — 2026-09-11

## Context

The default Linux PyTorch distribution pulls CUDA runtime libraries even though
the container has no GPU contract. On the first smoke build those libraries
filled the small local Docker disk before the image could be committed.

## Decision

Resolve `torch` from the explicit PyTorch CPU index on Linux while retaining the
platform-native PyPI resolution on macOS and Windows. The lockfile remains the
single source of truth for all platforms, and the container continues to use
`uv sync --locked`.

## Tradeoffs

CPU containers cannot use CUDA acceleration. That is appropriate for the
current runtime image, which exposes the CLI and library but does not promise
GPU scheduling. GPU deployments can provide a separate environment and index
policy without enlarging the default image.

## Consequences

Linux CI and Docker smoke tests use a substantially smaller, deterministic
runtime. The PyTorch index configuration is now part of the dependency
contract and must be revisited if GPU-backed container execution becomes a
supported deployment target.
