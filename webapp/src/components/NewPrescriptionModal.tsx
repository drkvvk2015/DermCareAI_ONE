import { Plus, Trash2, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { api, ApiError, type MedicationItem, type NewPrescription } from '../api/client';
import { useSession } from '../auth/Session';

type Props = {
  patientId: string;
  encounters: Array<Record<string, unknown>>;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

const defaultItem: MedicationItem = {
  medicine_id: 'MED-1',
  name: '',
  strength: '',
  dose: '',
  route: 'Topical',
  frequency: 'Twice daily',
  duration: '14 days',
  quantity: 1,
  instructions: '',
};

export function NewPrescriptionModal({ patientId, encounters, isOpen, onClose, onSuccess }: Props) {
  const { user } = useSession();
  const [encounterId, setEncounterId] = useState(String(encounters[0]?.id ?? ''));
  const [generalInstructions, setGeneralInstructions] = useState('');
  const [items, setItems] = useState<MedicationItem[]>([{ ...defaultItem }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  function addItem() {
    setItems((prev) => [
      ...prev,
      {
        ...defaultItem,
        medicine_id: `MED-${prev.length + 1}`,
      },
    ]);
  }

  function removeItem(index: number) {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  function updateItem<K extends keyof MedicationItem>(index: number, key: K, value: MedicationItem[K]) {
    setItems((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [key]: value };
      return next;
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    if (!encounterId) {
      setError('An active encounter is required to create a prescription.');
      return;
    }

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (!item.name.trim() || !item.strength.trim() || !item.dose.trim() || item.quantity <= 0) {
        setError(`Please fill all required fields (Name, Strength, Dose, Quantity) for Medication #${i + 1}.`);
        return;
      }
    }

    setBusy(true);
    setError('');

    const payload: NewPrescription = {
      patient_id: patientId,
      encounter_id: encounterId,
      instructions: generalInstructions.trim(),
      items: items.map((it) => ({
        ...it,
        name: it.name.trim(),
        strength: it.strength.trim(),
        dose: it.dose.trim(),
        route: it.route.trim(),
        frequency: it.frequency.trim(),
        duration: it.duration.trim(),
      })),
    };

    try {
      await api.createPrescription(payload, user);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create prescription.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title-rx">
      <div className="modal-card modal-card-large">
        <div className="modal-header">
          <div>
            <p className="eyebrow">PHARMACY INTEGRITY</p>
            <h2 id="modal-title-rx">Author Prescription</h2>
          </div>
          <button className="icon-action" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label htmlFor="rx-encounter">Linked Encounter *</label>
          <select
            id="rx-encounter"
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

          <label htmlFor="rx-instructions">General Prescription Instructions</label>
          <input
            id="rx-instructions"
            className="form-input"
            value={generalInstructions}
            onChange={(e) => setGeneralInstructions(e.target.value)}
            placeholder="e.g. Apply topicals after bath. Take oral tablets post-meals."
          />

          <div className="rx-items-header">
            <h3>Prescribed Medications ({items.length})</h3>
            <button className="secondary-button-small" type="button" onClick={addItem}>
              <Plus size={14} style={{ marginRight: 4 }} /> Add Medication
            </button>
          </div>

          <div className="rx-items-list">
            {items.map((item, index) => (
              <div key={index} className="rx-item-card">
                <div className="rx-item-row-top">
                  <strong>Medication #{index + 1}</strong>
                  {items.length > 1 && (
                    <button
                      className="icon-action-small"
                      type="button"
                      onClick={() => removeItem(index)}
                      title="Remove medication"
                      aria-label="Remove medication"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 10 }}>
                  <div>
                    <label htmlFor={`rx-name-${index}`}>Drug / Product Name *</label>
                    <input
                      id={`rx-name-${index}`}
                      className="form-input"
                      value={item.name}
                      onChange={(e) => updateItem(index, 'name', e.target.value)}
                      placeholder="e.g. Clobetasol Propionate Ointment"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor={`rx-strength-${index}`}>Strength *</label>
                    <input
                      id={`rx-strength-${index}`}
                      className="form-input"
                      value={item.strength}
                      onChange={(e) => updateItem(index, 'strength', e.target.value)}
                      placeholder="e.g. 0.05%"
                      required
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 }}>
                  <div>
                    <label htmlFor={`rx-dose-${index}`}>Dose *</label>
                    <input
                      id={`rx-dose-${index}`}
                      className="form-input"
                      value={item.dose}
                      onChange={(e) => updateItem(index, 'dose', e.target.value)}
                      placeholder="e.g. Thin layer"
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor={`rx-route-${index}`}>Route</label>
                    <select
                      id={`rx-route-${index}`}
                      className="form-input"
                      value={item.route}
                      onChange={(e) => updateItem(index, 'route', e.target.value)}
                    >
                      <option value="Topical">Topical</option>
                      <option value="Oral">Oral</option>
                      <option value="Intralesional">Intralesional</option>
                      <option value="Subcutaneous">Subcutaneous</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor={`rx-freq-${index}`}>Frequency</label>
                    <input
                      id={`rx-freq-${index}`}
                      className="form-input"
                      value={item.frequency}
                      onChange={(e) => updateItem(index, 'frequency', e.target.value)}
                      placeholder="e.g. Twice daily"
                    />
                  </div>
                  <div>
                    <label htmlFor={`rx-duration-${index}`}>Duration</label>
                    <input
                      id={`rx-duration-${index}`}
                      className="form-input"
                      value={item.duration}
                      onChange={(e) => updateItem(index, 'duration', e.target.value)}
                      placeholder="e.g. 14 days"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
            <button className="primary-button-inline" type="submit" disabled={busy || !user}>
              {busy ? 'Issuing...' : 'Issue Prescription'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
