"""Errors that map to exit code 2 (bad input or configuration)."""


class RegError(Exception):
    """Base class for usage, input and config errors (exit code 2)."""


class InputError(RegError):
    """A dataset, run, scores or baseline file is missing, malformed or inconsistent."""


class ConfigError(RegError):
    """The gate file is invalid."""
