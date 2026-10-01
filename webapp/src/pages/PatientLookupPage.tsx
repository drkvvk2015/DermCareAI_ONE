import { ArrowUpRight, Search, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

export function PatientLookupPage() {
  const [patientId, setPatientId] = useState('');
  const navigate = useNavigate();

  function openPatient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = patientId.trim();
    if (value) navigate(`/patients/${encodeURIComponent(value)}`);
  }

  return (
    <section className="content-page lookup-page">
      <div className="page-heading"><p className="eyebrow">PATIENT RECORDS</p><h1>Patient lookup</h1><p>Open an authorized patient record by its ID.</p></div>
      <form className="lookup-form" onSubmit={openPatient}>
        <label htmlFor="lookup-id">Patient ID</label>
        <div className="lookup-input"><Search size={19} /><input id="lookup-id" value={patientId} onChange={(event) => setPatientId(event.target.value)} placeholder="Enter patient ID" required /><button type="submit" aria-label="Open patient record" title="Open patient record"><ArrowUpRight size={19} /></button></div>
      </form>
      <div className="lookup-note"><ShieldCheck size={18} /><p>Record access is checked by the clinical service for your signed-in organization and role.</p></div>
    </section>
  );
}
