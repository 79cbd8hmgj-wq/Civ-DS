"""Structured errors returned by civds tooling."""


class CivDSError(Exception):
    """Base error for expected input or workspace failures."""


class FormatError(CivDSError):
    """The input is not a valid supported Nintendo DS structure."""


class UnsupportedROMError(CivDSError):
    """The ROM hash is absent from the supported-ROM registry."""
