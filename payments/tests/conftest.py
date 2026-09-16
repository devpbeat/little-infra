"""Shared pytest fixtures for the payments test suite.

Real outbound sockets are blocked by default via `--disable-socket` in
pyproject.toml. Tests that need to reach a real endpoint (rare, opt-in only)
should request pytest-socket's `socket_enabled` fixture explicitly rather
than relying on anything defined here.
"""
