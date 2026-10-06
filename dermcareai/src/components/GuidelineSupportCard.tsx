import React, { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Text, TextInput } from 'react-native-paper';
import {
  GUIDELINE_SOURCES,
  GuidelineRecommendation,
  GuidelineSource,
  guidelineApi,
} from '../services/clinicalApi';

type Props = { initialSymptoms?: string[]; initialConditions?: string[] };

const split = (value: string) => value.split(',').map(item => item.trim()).filter(Boolean);

const GuidelineSupportCard: React.FC<Props> = ({ initialSymptoms = [], initialConditions = [] }) => {
  const [counts, setCounts] = useState<Record<GuidelineSource, number> | null>(null);
  const [selected, setSelected] = useState<GuidelineSource[]>([]);
  const [symptoms, setSymptoms] = useState('');
  const [conditions, setConditions] = useState('');
  const [medications, setMedications] = useState('');
  const [allergies, setAllergies] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [matched, setMatched] = useState<boolean | null>(null);
  const [rec, setRec] = useState<GuidelineRecommendation | null>(null);

  useEffect(() => {
    guidelineApi.sources().then(r => setCounts(r.sources)).catch(() => setCounts(null));
  }, []);

  const toggle = (source: GuidelineSource) =>
    setSelected(current => (current.includes(source) ? current.filter(s => s !== source) : [...current, source]));

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await guidelineApi.recommend({
        symptoms: [...initialSymptoms, ...split(symptoms)],
        conditions: [...initialConditions, ...split(conditions)],
        medications: split(medications),
        allergies: split(allergies),
        sources: selected,
      });
      setMatched(result.matched);
      setRec(result.recommendation);
    } catch (err) {
      setMatched(null);
      setRec(null);
      setError(err instanceof Error ? err.message : 'Guideline support is unavailable');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <Card.Title title="Guideline support" subtitle="Suggestion only - the clinician decides" />
      <Card.Content>
        <Text style={styles.meta}>Does not diagnose or prescribe. Interactions and dosing are not evaluated. Select sources, or leave all unselected to search every source.</Text>
        <View style={styles.chips}>
          {GUIDELINE_SOURCES.map(source => (
            <Chip key={source} selected={selected.includes(source)} onPress={() => toggle(source)} style={styles.chip}>
              {source}{counts ? ` (${counts[source] ?? 0})` : ''}
            </Chip>
          ))}
        </View>
        <TextInput mode="outlined" label="Additional symptoms (comma separated)" value={symptoms} onChangeText={setSymptoms} style={styles.input} />
        <TextInput mode="outlined" label="Additional conditions (comma separated)" value={conditions} onChangeText={setConditions} style={styles.input} />
        <TextInput mode="outlined" label="Current medications" value={medications} onChangeText={setMedications} style={styles.input} />
        <TextInput mode="outlined" label="Allergies" value={allergies} onChangeText={setAllergies} style={styles.input} />
        <Button mode="outlined" onPress={submit} loading={busy} disabled={busy} style={styles.input}>Get guideline suggestion</Button>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {matched === false ? <Text style={styles.meta}>No approved guideline matched the selected sources.</Text> : null}
        {rec ? (
          <View style={styles.input}>
            <Text variant="titleSmall">{rec.summary}</Text>
            <Text style={styles.meta}>{rec.guideline_id} v{rec.guideline_version} | evidence {rec.evidence_quality} | approved by {rec.approved_by} on {rec.approved_on}</Text>
            {rec.escalation_required ? <Text style={styles.error}>Review recommended: possible contraindication or low confidence.</Text> : null}
            {rec.contraindications_flagged.length ? <Text>Possible contraindications: {rec.contraindications_flagged.join(', ')}</Text> : null}
            {rec.missing_information.length ? <Text>Missing information: {rec.missing_information.join(', ')}</Text> : null}
            {rec.alternatives.length ? <Text>Alternatives: {rec.alternatives.join('; ')}</Text> : null}
            {rec.notes.map(note => <Text key={note} style={styles.meta}>{note}</Text>)}
            <Text style={styles.meta}>{rec.citations.join(' | ')}</Text>
          </View>
        ) : null}
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  meta: { opacity: 0.7, marginTop: 4 },
  error: { color: '#b00020', marginTop: 4 },
  input: { marginTop: 8 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
  chip: { marginRight: 4 },
});

export default GuidelineSupportCard;
