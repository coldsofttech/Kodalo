"""Errors raised by the tunnel package. Messages are fit to show the user."""


class TunnelError(Exception):
    """The public address could not be set up: cloudflared is missing and could not be installed,
    or it did not start."""
