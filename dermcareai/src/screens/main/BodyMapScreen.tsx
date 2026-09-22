import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Chip, Snackbar, Text, TextInput } from 'react-native-paper';
import { NavigationProps } from '../../navigation/types';
import { encounterApi } from '../../services/clinicalApi';

const BODY_SITES = [
  'scalp','face','neck','chest','back','abdomen',
  'upper_limb','lower_limb','hand','foot','genital',
] as const;

const BodyMapScreen: React.FC<NavigationProps<'BodyMap'>> = ({ navigation, route }) => {
  const { encounterId, patient } = route.params;
  const [site, setSite] = useState<string>('face');
  const [lesionCode, setLesionCode] = useState('L-001');
  const [laterality, setLaterality] = useState('');
  const [sizeMm, setSizeMm] = useState('');
  const [morphology, setMorphology] = useState('');
  const [evolution, setEvolution] = useState('');
  const [impression, setImpression] = useState('');
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState('');

  const save = async () => {
    if (!site || !lesionCode.trim() || !morphology.trim()) {
      setSnack('Body site, lesion code and morphology are required');
      return;
    }
    setSaving(true);
    try {
      await encounterApi.saveLesion({
        patientId: patient.id,
        encounterId,
        lesionCode: lesionCode.trim(),
        bodySite: site,
        laterality: laterality.trim() || undefined,
        morphology: { primary: morphology.trim() },
        sizeMm: sizeMm ? Number(sizeMm) : undefined,
        evolution: evolution.trim() || undefined,
        clinicalImpression: impression.trim() || undefined,
        differential: [],
      });
      setSnack('Lesion added to longitudinal timeline');
    } catch (error) {
      setSnack(error instanceof Error ? error.message : 'Unable to save lesion');
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container}>
        <Card>
          <Card.Title title="Dermatology Body Map" subtitle={patient.name} />
          <Card.Content>
            <Text variant="titleMedium">Body site</Text>
            <View style={styles.chips}>
              {BODY_SITES.map(item => (
                <Chip
                  key={item}
                  selected={item === site}
                  onPress={() => setSite(item)}
                  style={styles.chip}
                >
                  {item.replace(/_/g, ' ')}
                </Chip>
              ))}
            </View>

            <TextInput
              mode="outlined"
              label="Lesion code"
              value={lesionCode}
              onChangeText={setLesionCode}
              style={styles.input}
            />
            <TextInput
              mode="outlined"
              label="Laterality"
              value={laterality}
              onChangeText={setLaterality}
              style={styles.input}
            />
            <TextInput
              mode="outlined"
              label="Morphology"
              value={morphology}
              onChangeText={setMorphology}
              style={styles.input}
              placeholder="e.g. plaque, papule, vesicle"
            />
            <TextInput
              mode="outlined"
              label="Size (mm)"
              value={sizeMm}
              onChangeText={setSizeMm}
              keyboardType="decimal-pad"
              style={styles.input}
            />
            <TextInput
              mode="outlined"
              label="Evolution"
              value={evolution}
              onChangeText={setEvolution}
              multiline
              style={styles.input}
            />
            <TextInput
              mode="outlined"
              label="Clinical impression"
              value={impression}
              onChangeText={setImpression}
              multiline
              style={styles.input}
            />
            <Button mode="contained" onPress={save} loading={saving} disabled={saving} style={styles.button}>
              Save Lesion
            </Button>
            <Button mode="text" onPress={() => navigation.goBack()} disabled={saving}>
              Back to Encounter
            </Button>
          </Card.Content>
        </Card>
      </ScrollView>
      <Snackbar visible={Boolean(snack)} onDismiss={() => setSnack('')} duration={3000}>
        {snack}
      </Snackbar>
    </View>
  );
};

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: { padding: 16 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  chip: { marginBottom: 4 },
  input: { marginTop: 10 },
  button: { marginTop: 18 },
});

export default BodyMapScreen;
