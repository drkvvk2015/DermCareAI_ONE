import { useEffect, useState } from 'react';
import { api, ApiError, GUIDELINE_SOURCES, type GuidelineResult, type GuidelineSource, type GuidelineSources } from '../api/client';
import { useSession } from '../auth/Session';

const split = (value: string) => value.split(',').map((item) => item.trim()).filter(Boolean);

export function GuidelinePanel() {
  const { user } = useSession();
  const [available, setAvailable] = useState<GuidelineSources | null>(null);
  const [selected, setSelected] = useState<GuidelineSource[]>([]);
  const [fields, setFields] = useState({ symptoms: '', conditions: '', medications: '', allergies: '' });
  const [result, setResult] = useState<GuidelineResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.guidelineSources(user).then(setAvailable).catch(() => setAvailable(null));
  }, [user]);

  const toggle = (source: GuidelineSource) => {
    setResult(null);
    setSelected((current) => (current.includes(source) ? current.filter((item) => item !== source) : [...current, source]));
  };

  const updateField = (key: keyof typeof fields, value: string) => {
    setResult(null);
    setFields((current) => ({ ...current, [key]: value }));
  };

  const submit = async () => {
    if (!user) return;
    setBusy(true);
    setError('');
    try {
      setResult(await api.recommendGuideline({
        symptoms: split(fields.symptoms),
        conditions: split(fields.conditions),
        medications: split(fields.medications),
        allergies: split(fields.allergies),
        sources: selected,
      }, user));
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : 'Guideline support is unavailable.');
    } finally {
      setBusy(false);
    }
  };

  const rec = result?.recommendation;
  return (
    <section className="summary-section" aria-labelledby="guideline-heading">
      <div className="section-title"><h2 id="guideline-heading">Guideline support</h2></div>
      <p><strong>Suggestion only.</strong> Guidance for the treating clinician; it does not make decisions, diagnose or prescribe. Interactions and dosing are not evaluated.</p>
      <fieldset disabled={busy}>
        <legend>Guideline sources (none selected = all)</legend>
        {GUIDELINE_SOURCES.map((source) => (
          <label key={source} style={{ marginRight: 12 }}>
            <input type="checkbox" checked={selected.includes(source)} onChange={() => toggle(source)} />
            {' '}{source}{available ? ` (${available[source] ?? 0})` : ''}
          </label>
        ))}
      </fieldset>
      {(['symptoms', 'conditions', 'medications', 'allergies'] as const).map((key) => (
        <label key={key} style={{ display: 'block', marginTop: 8 }}>
          {key[0].toUpperCase() + key.slice(1)} (comma separated, clinical terms only)
          <input value={fields[key]} onChange={(event) => updateField(key, event.target.value)} />
        </label>
      ))}
      <button type="button" disabled={busy} onClick={() => void submit()}>{busy ? 'Searching…' : 'Get suggestion'}</button>
      {error ? <p role="alert">{error}</p> : null}
      {result && !rec ? <p>No approved guideline matched the selected sources.</p> : null}
      {rec ? (
        <div>
          <h3>{rec.summary}</h3>
          <p>{rec.guideline_id} v{rec.guideline_version} · evidence {rec.evidence_quality} · approved by {rec.approved_by} on {rec.approved_on}</p>
          <dl>
            <dt>Evidence status</dt><dd>{rec.evidence_status}</dd>
            <dt>Source identifier</dt><dd>{rec.source_identifier}</dd>
            <dt>Publication date</dt><dd>{rec.publication_date}</dd>
            <dt>Retrieved at</dt><dd>{rec.retrieved_at}</dd>
          </dl>
          {rec.escalation_required ? <p role="alert">Review recommended: possible contraindication or low heuristic score.</p> : null}
          {rec.contraindications_flagged.length ? <p>Possible contraindications: {rec.contraindications_flagged.join(', ')}</p> : null}
          {rec.missing_information.length ? <p>Missing information: {rec.missing_information.join(', ')}</p> : null}
          {rec.alternatives.length ? <p>Alternatives: {rec.alternatives.join('; ')}</p> : null}
          <ul>{rec.notes.map((note) => <li key={note}>{note}</li>)}</ul>
          <small>{rec.citations.join(' · ')}</small>
        </div>
      ) : null}
    </section>
  );
}
