import { CheckCircle2, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import { useSession } from '../auth/Session';

type Props = {
  encounterId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

export function SignoffModal({ encounterId, isOpen, onClose, onSuccess }: Props) {
  const { user } = useSession();
  const [attestation, setAttestation] = useState(
    'I reviewed the encounter documentation and clinical decision-making.'
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  async function handleSign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    if (attestation.trim().length < 20) {
      setError('Attestation statement must be at least 20 characters long.');
      return;
    }

    setBusy(true);
    setError('');

    try {
      await api.signEncounter(encounterId, attestation.trim(), user);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign off encounter.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title-signoff">
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <p className="eyebrow">CLINICAL ATTESTATION</p>
            <h2 id="modal-title-signoff">Sign Off Encounter</h2>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSign} className="modal-form">
          <p className="modal-description">
            Signing locks the encounter as authoritative clinical truth. Any attached AI decision support
            must be explicitly reviewed, and all core dermatology documentation fields must be present.
          </p>

          <label htmlFor="signoff-attestation">Doctor Attestation Statement *</label>
          <textarea
            id="signoff-attestation"
            className="form-input form-textarea"
            rows={3}
            value={attestation}
            onChange={(e) => setAttestation(e.target.value)}
            required
            maxLength={500}
          />

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button className="primary-button-inline" type="submit" disabled={busy || !user}>
              <CheckCircle2 size={16} style={{ marginRight: 6 }} />
              {busy ? 'Signing...' : 'Confirm Sign-off'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
