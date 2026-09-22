import React, { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { Button, Card, Text, useTheme } from 'react-native-paper';
import { NavigationProps } from '../../navigation/types';
import { encounterApi } from '../../services/clinicalApi';

const NewEncounterScreen: React.FC<NavigationProps<'NewEncounter'>> = ({ navigation, route }) => {
  const theme = useTheme();
  const { patient } = route.params;
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const startEncounter = async () => {
    setCreating(true);
    setError('');
    try {
      const encounter = await encounterApi.create(patient.id);
      navigation.replace('Encounter', { encounterId: encounter.id, patient });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to start encounter');
    } finally {
      setCreating(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card>
        <Card.Content>
          <Text variant="headlineSmall">Start clinical encounter</Text>
          <Text style={styles.patient}>{patient.name}</Text>
          <Text style={styles.meta}>{patient.age} years • {patient.gender}</Text>
          <Text style={styles.help}>The encounter workspace keeps the clinical note, dermatology examination, assessment, follow-up and sign-off together.</Text>
          {error ? <Text style={{ color: theme.colors.error }}>{error}</Text> : null}
          <Button mode="contained" onPress={startEncounter} loading={creating} disabled={creating} style={styles.button}>Open Encounter Workspace</Button>
        </Card.Content>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16 },
  patient: { fontSize: 22, fontWeight: '700', marginTop: 16 },
  meta: { opacity: 0.7, marginTop: 4 },
  help: { marginTop: 16, lineHeight: 21 },
  button: { marginTop: 20 },
});

export default NewEncounterScreen;