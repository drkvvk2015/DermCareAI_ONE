# Pharmacy production checklist

Before using dispensing in a live pharmacy:

- Use a transactional database with row-level locking for stock changes.
- Enforce role-based permissions for pharmacist/pharmacy manager actions.
- Store batch number, expiry, supplier, purchase price, selling price and tax metadata.
- Prevent dispensing of expired or blocked batches.
- Implement FIFO/FEFO stock selection as appropriate.
- Record every purchase, adjustment, transfer, return, dispense and cancellation in the audit trail.
- Require prescription linkage where legally/clinically required.
- Add controlled-drug workflows only after a jurisdiction-specific compliance review.
- Reconcile physical stock against digital stock regularly.
- Keep patient health information out of public social media integrations.
