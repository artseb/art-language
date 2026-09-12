"""Internal control-flow signals (not ART-visible errors - see
art/errors.py for ReturnSignal, which lives there since so much of the
error-handling code already reasons about it alongside ArtError)."""


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass
