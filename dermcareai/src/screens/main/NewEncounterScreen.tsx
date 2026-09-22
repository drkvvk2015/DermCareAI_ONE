import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { Button, Card, RadioButton, Text, useTheme } from 'react-native-paper';
import { NavigationProps } from '../../navigation/types';
import { dermatologyTemplateApi, DermatologyTemplate, encounterApi } from '../../services/clinicalApi';

const NewEncounterScreen: React.FC<NavigationProps<'NewEncounter'>> = ({ navigation, route }) => {
  const theme = useTheme();
  const { patient } = route.params;
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [templates, setTemplates] = useState<DermatologyTemplate[]>([]);
  const [template, setTemplate] = useState('');

  useEffect(() => {
    let active = true;
    dermatologyTemplateApi.list().then((response) => {
      if (active) setTemplates(response.templates);
    }).catch(() => {
      if (active) setTemplates([]);
    });
    return () => { active = false; };
  }, []);

  const startEncounter = async () => {
    setCreating(true);
    setError('');
    try {
      const encounter = await encounterApi.create(patient.id, { template: template || undefined });
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
          {templates.length > 0 ? (
            <Card style={styles.templateCard} mode="outlined">
              <Card.Content>
                <Text variant="titleMedium">History template</Text>
                <Text style={styles.templateHelp}>Choose a structured dermatology template for this encounter.</Text>
                <RadioButton.Group onValueChange={setTemplate} value={template}>
                  {templates.map((item) => (
                    <RadioButton.Item key={item.condition} label={item.condition.replace(/_/g, ' ')} value={item.condition} />
                  ))}
                </RadioButton.Group>
              </Card.Content>
            </Card>
          ) : null}
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
  templateCard: { marginTop: 16 },
  templateHelp: { marginTop: 4, opacity: 0.7 },
});

export default NewEncounterScreen;