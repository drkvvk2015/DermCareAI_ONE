# Pharmacy inventory engine

This slice adds deterministic **FEFO (first-expiry, first-out)** allocation and
batch validation. It intentionally does not bypass the existing commerce
transaction boundary.

Production integration still requires persisted batch-level rows, row locking,
audit events, prescription policy, and jurisdiction-specific controlled-drug
rules before live dispensing.
