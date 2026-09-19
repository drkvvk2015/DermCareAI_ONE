import React, { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Divider, Snackbar, Text, TextInput, ActivityIndicator } from 'react-native-paper';
import { NavigationProps } from '../../navigation/types';
import { ClinicalAIReview, ClinicalEncounter, encounterApi } from '../../services/clinicalApi';

const EncounterScreen: React.FC<NavigationProps<'Encounter'>> = ({ route }) => {
  const { encounterId, patient } = route.params;
  const [encounter, setEncounter] = useState<ClinicalEncounter | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [snack, setSnack] = useState('');

  const [chiefComplaint, setChiefComplaint] = useState('');
  const [onsetDuration, setOnsetDuration] = useState('');
  const [progression, setProgression] = useState('');
  const [pruritus, setPruritus] = useState('');
  const [pain, setPain] = useState('');
  const [distribution, setDistribution] = useState('');
  const [primaryMorphology, setPrimaryMorphology] = useState('');
  const [surface, setSurface] = useState('');
  const [color, setColor] = useState('');
  const [border, setBorder] = useState('');
  const [size, setSize] = useState('');
  const [dermoscopy, setDermoscopy] = useState('');
  const [systemicSymptoms, setSystemicSymptoms] = useState('');
  const [provisionalDiagnosis, setProvisionalDiagnosis] = useState('');
  const [differential, setDifferential] = useState('');
  const [managementPlan, setManagementPlan] = useState('');
  const [followupAt, setFollowupAt] = useState('');
  const [followupInstructions, setFollowupInstructions] = useState('');
  const [aiReviews, setAIReviews] = useState<ClinicalAIReview[]>([]);

  const readForm = (record: ClinicalEncounter) => {
    const complaints = record.complaints || {};
    const exam = (record.examination?.dermatology || {}) as Record<string, unknown>;
    const assessment = record.assessment || {};
    const plan = record.plan || {};
    setChiefComplaint(String(complaints.chief_complaint || ''));
    setOnsetDuration(String(exam.onset_duration || ''));
    setProgression(String(exam.progression || ''));
    setPruritus(String(exam.pruritus || ''));
    setPain(String(exam.pain || ''));
    setDistribution(String(exam.distribution || ''));
    setPrimaryMorphology(String(exam.primary_morphology || ''));
    setSurface(String(exam.surface || ''));
    setColor(String(exam.color || ''));
    setBorder(String(exam.border || ''));
    setSize(String(exam.size_mm || ''));
    setDermoscopy(String(exam.dermoscopy || ''));
    setSystemicSymptoms(String(exam.systemic_symptoms || ''));
    setProvisionalDiagnosis(String(assessment.provisional_diagnosis || ''));
    setDifferential(Array.isArray(assessment.differential) ? assessment.differential.join(', ') : String(assessment.differential || ''));
    setManagementPlan(String(plan.management_plan || ''));
  };

  const load = async () => {
    setLoading(true);
    try {
      const data = await encounterApi.get(encounterId);
      setEncounter(data);
      readForm(data);
      setAIReviews(await encounterApi.listAIReviews(encounterId));
    } catch (err) {
      setSnack(err instanceof Error ? err.message : 'Unable to load encounter');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [encounterId]);

  const payload = useMemo(() => ({
    complaints: { chief_complaint: chiefComplaint },
    examination: { dermatology: {
      onset_duration: onsetDuration, progression, pruritus, pain, distribution,
      primary_morphology: primaryMorphology, surface, color, border, size_mm: size,
      dermoscopy, systemic_symptoms: systemicSymptoms,
    }},
    assessment: {
      provisional_diagnosis: provisionalDiagnosis,
      differential: differential.split(',').map(item => item.trim()).filter(Boolean),
    },
    plan: { management_plan: managementPlan },
  }), [chiefComplaint, onsetDuration, progression, pruritus, pain, distribution, primaryMorphology, surface, color, border, size, dermoscopy, systemicSymptoms, provisionalDiagnosis, differential, managementPlan]);

  const save = async () => {
    if (!encounter || encounter.status === 'signed') return;
    setSaving(true);
    try {
      const updated = await encounterApi.update(encounter.id, encounter.version, payload);
      setEncounter(updated);
      setSnack('Encounter saved');
    } catch (err) {
      setSnack(err instanceof Error ? err.message : 'Unable to save. Reload if another user updated this encounter.');
    } finally { setSaving(false); }
  };

  const planFollowup = async () => {
    if (!encounter || !followupAt || !followupInstructions.trim() || encounter.status === 'signed') return;
    try {
      await encounterApi.addFollowup(encounter.id, followupAt, followupInstructions.trim());
      setSnack('Follow-up planned');
      setFollowupInstructions('');
    } catch (err) { setSnack(err instanceof Error ? err.message : 'Unable to plan follow-up'); }
  };

  const sign = async () => {
    if (!encounter || encounter.status === 'signed') return;
    setSigning(true);
    try {
      await save();
      await encounterApi.sign(encounter.id, 'I reviewed the documented history, examination, assessment and plan and accept responsibility for the clinical record.');
      setEncounter(prev => prev ? { ...prev, status: 'signed' } : prev);
      setSnack('Encounter signed');
    } catch (err) { setSnack(err instanceof Error ? err.message : 'Unable to sign encounter'); }
    finally { setSigning(false); }
  };

  if (loading) return <View style={styles.center}><ActivityIndicator /></View>;
  if (!encounter) return <View style={styles.center}><Text>Encounter not available.</Text><Button onPress={load}>Retry</Button></View>;

  const signed = encounter.status === 'signed';
  return (
    <View style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container}>
        <Card><Card.Content>
          <Text variant="headlineSmall">{patient.name}</Text>
          <Text style={styles.meta}>Encounter {encounter.id} • {encounter.status}</Text>
          <View style={styles.chips}>
            <Chip icon={signed ? 'check-circle' : 'pencil'}>{signed ? 'Signed' : 'Draft'}</Chip>
            {aiReviews.length ? <Chip icon="brain">{aiReviews.length} AI review{aiReviews.length > 1 ? 's' : ''}</Chip> : null}
          </View>
        </Card.Content></Card>

        <Card><Card.Title title="History" subtitle="Presenting complaint and evolution" /><Card.Content>
          <TextInput mode="outlined" label="Chief complaint" value={chiefComplaint} onChangeText={setChiefComplaint} disabled={signed} multiline />
          <TextInput mode="outlined" label="Onset / duration" value={onsetDuration} onChangeText={setOnsetDuration} disabled={signed} style={styles.input} />
          <TextInput mode="outlined" label="Progression / change" value={progression} onChangeText={setProgression} disabled={signed} style={styles.input} />
          <View style={styles.row}><TextInput mode="outlined" label="Pruritus" value={pruritus} onChangeText={setPruritus} disabled={signed} style={styles.half} /><TextInput mode="outlined" label="Pain" value={pain} onChangeText={setPain} disabled={signed} style={styles.half} /></View>
          <TextInput mode="outlined" label="Distribution / sites" value={distribution} onChangeText={setDistribution} disabled={signed} style={styles.input} />
          <TextInput mode="outlined" label="Systemic symptoms / red flags" value={systemicSymptoms} onChangeText={setSystemicSymptoms} disabled={signed} style={styles.input} multiline />
        </Card.Content></Card>

        <Card><Card.Title title="Dermatology examination" subtitle="Structured lesion description" /><Card.Content>
          <TextInput mode="outlined" label="Primary morphology" value={primaryMorphology} onChangeText={setPrimaryMorphology} disabled={signed} />
          <TextInput mode="outlined" label="Surface / secondary change" value={surface} onChangeText={setSurface} disabled={signed} style={styles.input} />
          <View style={styles.row}><TextInput mode="outlined" label="Color" value={color} onChangeText={setColor} disabled={signed} style={styles.half} /><TextInput mode="outlined" label="Border" value={border} onChangeText={setBorder} disabled={signed} style={styles.half} /></View>
          <TextInput mode="outlined" label="Size (mm)" value={size} onChangeText={setSize} disabled={signed} keyboardType="decimal-pad" style={styles.input} />
          <TextInput mode="outlined" label="Dermoscopy findings" value={dermoscopy} onChangeText={setDermoscopy} disabled={signed} style={styles.input} multiline />
        </Card.Content></Card>

        <Card><Card.Title title="Assessment & plan" /><Card.Content>
          <TextInput mode="outlined" label="Provisional diagnosis" value={provisionalDiagnosis} onChangeText={setProvisionalDiagnosis} disabled={signed} />
          <TextInput mode="outlined" label="Differential diagnoses (comma separated)" value={differential} onChangeText={setDifferential} disabled={signed} style={styles.input} multiline />
          <TextInput mode="outlined" label="Management plan" value={managementPlan} onChangeText={setManagementPlan} disabled={signed} style={styles.input} multiline />
        </Card.Content></Card>

        {aiReviews.length ? <Card><Card.Title title="AI decision-support review" subtitle="Clinician review remains required" /><Card.Content>{aiReviews.map(review => <View key={review.id} style={styles.aiBlock}><Text variant="titleMedium">{review.predicted_label}</Text><Text>Confidence: {(review.confidence * 100).toFixed(1)}%</Text><Text>Model: {review.model_name}</Text><Text>Decision: {review.clinician_decision || 'Pending clinician review'}</Text>{review.clinician_override_label ? <Text>Override: {review.clinician_override_label}</Text> : null}<Divider style={styles.input} /></View>)}</Card.Content></Card> : null}

        <Card><Card.Title title="Follow-up" subtitle="Record the intended review point" /><Card.Content>
          <TextInput mode="outlined" label="Due date/time (ISO 8601)" value={followupAt} onChangeText={setFollowupAt} disabled={signed} />
          <TextInput mode="outlined" label="Follow-up instructions" value={followupInstructions} onChangeText={setFollowupInstructions} disabled={signed} style={styles.input} multiline />
          <Button mode="outlined" onPress={planFollowup} disabled={signed || !followupAt || !followupInstructions.trim()} style={styles.button}>Plan Follow-up</Button>
        </Card.Content></Card>

        {!signed ? <View style={styles.actions}><Button mode="outlined" onPress={save} loading={saving} disabled={saving} style={styles.button}>Save Encounter</Button><Button mode="contained" onPress={sign} loading={signing} disabled={saving || signing} style={styles.button}>Review & Sign Encounter</Button></View> : <Card><Card.Content><Text>Signed clinical record. Editing is disabled to preserve the signed state.</Text></Card.Content></Card>}
      </ScrollView>
      <Snackbar visible={Boolean(snack)} onDismiss={() => setSnack('')} duration={3500}>{snack}</Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: 16, gap: 14 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  meta: { opacity: 0.7, marginTop: 4 },
  chips: { flexDirection: 'row', gap: 8, marginTop: 12 },
  input: { marginTop: 10 },
  row: { flexDirection: 'row', gap: 10, marginTop: 10 },
  half: { flex: 1 },
  aiBlock: { paddingVertical: 4 },
  actions: { paddingBottom: 32, gap: 10 },
  button: { marginTop: 4 },
});

export default EncounterScreen;