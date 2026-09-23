import React, { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Snackbar, Text, TextInput } from 'react-native-paper';
import type { NavigationProps } from '../../navigation/types';
import { api } from '../../services/api';

type Props = NavigationProps<'Prescription'>;
type Medication = { medicine_id: string; name: string; strength: string; dose: string; route: string; frequency: string; duration: string; quantity: string; instructions: string };
const blankMedication = (): Medication => ({ medicine_id: '', name: '', strength: '', dose: '', route: 'topical', frequency: 'once daily', duration: '', quantity: '1', instructions: '' });

const PrescriptionScreen = ({ route }: Props) => {
  const { patient, encounterId } = route.params;
  const [items, setItems] = useState<Medication[]>([blankMedication()]);
  const [instructions, setInstructions] = useState('');
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState('');
  const updateItem = useCallback((index: number, patch: Partial<Medication>) => { setItems(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item)); }, []);
  const save = async () => {
    if (items.some(item => !item.medicine_id.trim() || !item.name.trim() || !item.strength.trim() || !item.dose.trim() || !item.route.trim() || !item.frequency.trim() || !item.duration.trim() || Number(item.quantity) <= 0)) { setSnack('Complete all required medication fields before saving.'); return; }
    setSaving(true);
    try {
      await api.createPrescription({ patient_id: patient.id, encounter_id: encounterId, instructions, items: items.map(item => ({ ...item, medicine_id: item.medicine_id.trim(), name: item.name.trim(), quantity: Number(item.quantity) })) });
      setSnack('Prescription saved to the clinical record.'); setItems([blankMedication()]); setInstructions('');
    } catch (error) { setSnack(error instanceof Error ? error.message : 'Unable to save prescription.'); } finally { setSaving(false); }
  };
  return (
    <View style={styles.flex}><ScrollView contentContainerStyle={styles.container}>
      <Card><Card.Title title="Dermatology prescription" subtitle={patient.name} /><Card.Content>
        <Text variant="bodyMedium">Linked encounter: {encounterId}</Text>
        <TextInput mode="outlined" label="General instructions" value={instructions} onChangeText={setInstructions} multiline style={styles.input} />
      </Card.Content></Card>
      {items.map((item, index) => <Card key={index}><Card.Title title={'Medication ' + (index + 1)} /><Card.Content>
        <TextInput mode="outlined" label="Medicine ID" value={item.medicine_id} onChangeText={medicine_id => updateItem(index, { medicine_id })} />
        <TextInput mode="outlined" label="Medicine name" value={item.name} onChangeText={name => updateItem(index, { name })} style={styles.input} />
        <TextInput mode="outlined" label="Strength" value={item.strength} onChangeText={strength => updateItem(index, { strength })} style={styles.input} />
        <View style={styles.row}><TextInput mode="outlined" label="Dose" value={item.dose} onChangeText={dose => updateItem(index, { dose })} style={styles.half} /><TextInput mode="outlined" label="Route" value={item.route} onChangeText={route => updateItem(index, { route })} style={styles.half} /></View>
        <View style={styles.row}><TextInput mode="outlined" label="Frequency" value={item.frequency} onChangeText={frequency => updateItem(index, { frequency })} style={styles.half} /><TextInput mode="outlined" label="Duration" value={item.duration} onChangeText={duration => updateItem(index, { duration })} style={styles.half} /></View>
        <TextInput mode="outlined" label="Quantity" value={item.quantity} onChangeText={quantity => updateItem(index, { quantity })} keyboardType="decimal-pad" style={styles.input} />
        <TextInput mode="outlined" label="Medication instructions" value={item.instructions} onChangeText={instructions => updateItem(index, { instructions })} multiline style={styles.input} />
        {items.length > 1 ? <Button mode="text" onPress={() => setItems(current => current.filter((_, itemIndex) => itemIndex !== index))}>Remove medication</Button> : null}
      </Card.Content></Card>)}
      <Button mode="outlined" icon="plus" onPress={() => setItems(current => [...current, blankMedication()])}>Add medication</Button>
      <Button mode="contained" icon="content-save" loading={saving} disabled={saving} onPress={() => void save()} style={styles.save}>Save prescription</Button>
    </ScrollView><Snackbar visible={Boolean(snack)} onDismiss={() => setSnack('')} duration={3500}>{snack}</Snackbar></View>
  );
};
const styles = StyleSheet.create({ flex: { flex: 1 }, container: { padding: 16, gap: 14 }, input: { marginTop: 10 }, row: { flexDirection: 'row', gap: 10, marginTop: 10 }, half: { flex: 1 }, save: { marginBottom: 24 } });
export default PrescriptionScreen;