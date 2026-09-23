# Billing arithmetic boundary

The existing commerce API remains responsible for invoice persistence and payment
providers. This module isolates money arithmetic using Decimal and explicit
rounding, avoiding binary floating-point decisions in the calculation core.

Provider webhooks remain authoritative for payment settlement and must continue
to be signature-verified and idempotent.
