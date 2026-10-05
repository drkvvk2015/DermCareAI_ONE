import { ArrowUpRight, Search, ShieldCheck } from 'lucide-react';
import { useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { useSession } from '../auth/Session';

const emptyPatient = { name: '', age: '', gender: 'male', phone: '', email: '', address: '', medicalHistory: '', allergies: '', currentMedications: '' };
type PatientForm = typeof emptyPatient;

export function PatientLookupPage() {
  const [patientId, setPatientId] = useState('');
  const [form, setForm] = useState<PatientForm>(emptyPatient);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const idempotencyKey = useRef<string>(crypto.randomUUID());
  const { user } = useSession();
  const navigate = useNavigate();

  function openPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = patientId.trim();
    if (value) navigate(`/patients/${encodeURIComponent(value)}`);
  }

  function updateField(field: keyof PatientForm, value: string) {
    // A changed payload needs a new key; the server rejects key reuse with different content.
    idempotencyKey.current = crypto.randomUUID();
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function registerPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user) return;
    const age = Number(form.age);
    if (!form.name.trim() || !Number.isInteger(age) || age < 0 || age > 130) {
      setError('Enter the patient name and a valid age.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const created = await api.createPatient({ ...form, name: form.name.trim(), age, gender: form.gender as 'male' | 'female' | 'other' }, user, idempotencyKey.current);
      idempotencyKey.current = crypto.randomUUID();
      setForm(emptyPatient);
      navigate(`/patients/${encodeURIComponent(created.id)}`);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'The patient could not be registered. Check your connection and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content-page lookup-page">
      <div className="page-heading"><p className="eyebrow">PATIENT RECORDS</p><h1>Patient lookup</h1><p>Open an authorized patient record by its ID.</p></div>
      <form className="lookup-form" onSubmit={openPatient}>
        <label htmlFor="lookup-id">Patient ID</label>
        <div className="lookup-input"><Search size={19} /><input id="lookup-id" value={patientId} onChange={(event) => setPatientId(event.target.value)} placeholder="Enter patient ID" required /><button type="submit" aria-label="Open patient record" title="Open patient record"><ArrowUpRight size={19} /></button></div>
      </form>
      <div className="lookup-note"><ShieldCheck size={18} /><p>Record access is checked by the clinical service for your signed-in organization and role.</p></div>
      <form className="login-form" onSubmit={registerPatient} style={{ marginTop: 32, maxWidth: 610, width: '100%' }}>
        <h2>Register patient</h2>
        <label htmlFor="patient-name">Full name</label>
        <input id="patient-name" value={form.name} onChange={(event) => updateField('name', event.target.value)} maxLength={200} required />
        <label htmlFor="patient-age">Age</label>
        <input id="patient-age" type="number" min={0} max={130} value={form.age} onChange={(event) => updateField('age', event.target.value)} required />
        <label htmlFor="patient-gender">Gender</label>
        <select id="patient-gender" value={form.gender} onChange={(event) => updateField('gender', event.target.value)} style={{ width: '100%', height: 44 }}>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
        <label htmlFor="patient-phone">Phone</label>
        <input id="patient-phone" type="tel" value={form.phone} onChange={(event) => updateField('phone', event.target.value)} maxLength={50} />
        <label htmlFor="patient-email">Email</label>
        <input id="patient-email" type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} maxLength={254} autoComplete="off" />
        <label htmlFor="patient-address">Address</label>
        <input id="patient-address" value={form.address} onChange={(event) => updateField('address', event.target.value)} maxLength={1000} />
        <label htmlFor="patient-history">Medical history</label>
        <input id="patient-history" value={form.medicalHistory} onChange={(event) => updateField('medicalHistory', event.target.value)} maxLength={5000} />
        <label htmlFor="patient-allergies">Allergies</label>
        <input id="patient-allergies" value={form.allergies} onChange={(event) => updateField('allergies', event.target.value)} maxLength={2000} />
        <label htmlFor="patient-medications">Current medications</label>
        <input id="patient-medications" value={form.currentMedications} onChange={(event) => updateField('currentMedications', event.target.value)} maxLength={2000} />
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <button className="primary-button" type="submit" disabled={busy || !user}>{busy ? 'Registering...' : 'Register patient'}</button>
      </form>
    </section>
  );
}
