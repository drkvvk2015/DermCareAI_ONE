import { X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError, type NewLesion } from '../api/client';
import { useSession } from '../auth/Session';

type Props = {
  patientId: string;
  encounters: Array<Record<string, unknown>>;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

const BODY_SITES = [
  { value: 'scalp', label: 'Scalp' },
  { value: 'face', label: 'Face' },
  { value: 'neck', label: 'Neck' },
  { value: 'chest', label: 'Chest' },
  { value: 'back', label: 'Back' },
  { value: 'abdomen', label: 'Abdomen' },
  { value: 'upper_limb', label: 'Upper Limb' },
  { value: 'lower_limb', label: 'Lower Limb' },
  { value: 'hand', label: 'Hand' },
  { value: 'foot', label: 'Foot' },
  { value: 'genital', label: 'Genital' },
];

export function NewLesionModal({ patientId, encounters, isOpen, onClose, onSuccess }: Props) {
  const { user } = useSession();
  const [encounterId, setEncounterId] = useState(String(encounters[0]?.id ?? ''));
  const [lesionCode, setLesionCode] = useState(`L-${encounters.length + 1}`);
  const [bodySite, setBodySite] = useState('face');
  const [laterality, setLaterality] = useState('left');
  const [sizeMm, setSizeMm] = useState('5');
  const [morphology, setMorphology] = useState('');
  const [clinicalImpression, setClinicalImpression] = useState('');
  const [differential, setDifferential] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    if (!encounterId) {
      setError('An active encounter is required to register a lesion.');
      return;
    }
    if (!lesionCode.trim() || !morphology.trim() || !clinicalImpression.trim()) {
      setError('Lesion code, morphology, and clinical impression are required.');
      return;
    }

    setBusy(true);
    setError('');

    const payload: NewLesion = {
      patient_id: patientId,
      encounter_id: encounterId,
      lesion_code: lesionCode.trim(),
      body_site: bodySite,
      laterality: laterality || undefined,
      size_mm: sizeMm ? Number(sizeMm) : undefined,
      morphology: {
        primary: morphology.trim(),
      },
      clinical_impression: clinicalImpression.trim(),
      differential: differential.split(',').map((s) => s.trim()).filter(Boolean),
    };

    try {
      await api.createLesion(payload, user);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to record lesion.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title-lesion">
      <div className="modal-card">
        <div className="modal-header">
          <div>
            <p className="eyebrow">LONGITUDINAL TRACKING</p>
            <h2 id="modal-title-lesion">Record Lesion</h2>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label htmlFor="lesion-encounter">Encounter *</label>
          <select
            id="lesion-encounter"
            className="form-input"
            value={encounterId}
            onChange={(e) => setEncounterId(e.target.value)}
            required
          >
            {encounters.map((enc) => (
              <option key={String(enc.id)} value={String(enc.id)}>
                {String(enc.id)} ({String(enc.status || 'open')})
              </option>
            ))}
          </select>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label htmlFor="lesion-code">Lesion Code *</label>
              <input
                id="lesion-code"
                className="form-input"
                value={lesionCode}
                onChange={(e) => setLesionCode(e.target.value)}
                placeholder="e.g. L-01"
                required
              />
            </div>
            <div>
              <label htmlFor="lesion-size">Size (mm)</label>
              <input
                id="lesion-size"
                type="number"
                step="0.1"
                min="0"
                className="form-input"
                value={sizeMm}
                onChange={(e) => setSizeMm(e.target.value)}
                placeholder="e.g. 6.5"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label htmlFor="lesion-site">Body Site *</label>
              <select
                id="lesion-site"
                className="form-input"
                value={bodySite}
                onChange={(e) => setBodySite(e.target.value)}
              >
                {BODY_SITES.map((site) => (
                  <option key={site.value} value={site.value}>
                    {site.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="lesion-laterality">Laterality</label>
              <select
                id="lesion-laterality"
                className="form-input"
                value={laterality}
                onChange={(e) => setLaterality(e.target.value)}
              >
                <option value="left">Left</option>
                <option value="right">Right</option>
                <option value="bilateral">Bilateral</option>
                <option value="midline">Midline</option>
              </select>
            </div>
          </div>

          <label htmlFor="lesion-morphology">Morphology & Color *</label>
          <input
            id="lesion-morphology"
            className="form-input"
            value={morphology}
            onChange={(e) => setMorphology(e.target.value)}
            placeholder="e.g. Asymmetric brown-black macule with irregular borders"
            required
          />

          <label htmlFor="lesion-impression">Clinical Impression *</label>
          <input
            id="lesion-impression"
            className="form-input"
            value={clinicalImpression}
            onChange={(e) => setClinicalImpression(e.target.value)}
            placeholder="e.g. Atypical melanocytic proliferation"
            required
          />

          <label htmlFor="lesion-differential">Differential Diagnoses (comma-separated)</label>
          <input
            id="lesion-differential"
            className="form-input"
            value={differential}
            onChange={(e) => setDifferential(e.target.value)}
            placeholder="e.g. Melanoma, Dysplastic Nevus, Seborrheic Keratosis"
          />

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button className="primary-button-inline" type="submit" disabled={busy || !user}>
              {busy ? 'Saving...' : 'Record Lesion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
