import React, { useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import {
  TextInput,
  Button,
  Text,
  Surface,
  useTheme,
  SegmentedButtons,
} from 'react-native-paper';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { patientRegistrationApi } from '../../services/clinicalApi';
import { isClinicalApiError } from '../../types/clinicalApi';

type AddPatientScreenProps = {
  navigation: NativeStackNavigationProp<any>;
};

const newIdempotencyKey = () => `patient-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const AddPatientScreen: React.FC<AddPatientScreenProps> = ({ navigation }) => {
  const theme = useTheme();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const idempotencyKey = useRef(newIdempotencyKey());
  const [formData, setFormDataState] = useState({
    name: '',
    age: '',
    gender: 'male',
    phone: '',
    email: '',
    address: '',
    medicalHistory: '',
    allergies: '',
    currentMedications: '',
  });

  // A changed payload needs a new key; the server rejects key reuse with different content.
  const setFormData = (next: typeof formData) => {
    idempotencyKey.current = newIdempotencyKey();
    setFormDataState(next);
  };

  const handleSubmit = async () => {
    const age = Number(formData.age);
    if (!formData.name.trim() || !formData.age.trim()) {
      setError('Please fill in all required fields');
      return;
    }
    if (!Number.isInteger(age) || age < 0 || age > 130) {
      setError('Enter a valid age');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await patientRegistrationApi.create(
        { ...formData, name: formData.name.trim(), age },
        idempotencyKey.current,
      );
      idempotencyKey.current = newIdempotencyKey();
      navigation.goBack();
    } catch (err: unknown) {
      setError(isClinicalApiError(err) ? err.message : 'The patient could not be registered. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Surface style={styles.surface}>
          <Text style={styles.title}>Add New Patient</Text>

          <TextInput
            label="Full Name *"
            value={formData.name}
            onChangeText={text => setFormData({ ...formData, name: text })}
            mode="outlined"
            style={styles.input}
          />

          <TextInput
            label="Age *"
            value={formData.age}
            onChangeText={text => setFormData({ ...formData, age: text })}
            mode="outlined"
            style={styles.input}
            keyboardType="numeric"
          />

          <Text style={styles.label}>Gender</Text>
          <SegmentedButtons
            value={formData.gender}
            onValueChange={value => setFormData({ ...formData, gender: value })}
            buttons={[
              { value: 'male', label: 'Male' },
              { value: 'female', label: 'Female' },
              { value: 'other', label: 'Other' },
            ]}
            style={styles.segmentedButtons}
          />

          <TextInput
            label="Phone Number"
            value={formData.phone}
            onChangeText={text => setFormData({ ...formData, phone: text })}
            mode="outlined"
            style={styles.input}
            keyboardType="phone-pad"
          />

          <TextInput
            label="Email"
            value={formData.email}
            onChangeText={text => setFormData({ ...formData, email: text })}
            mode="outlined"
            style={styles.input}
            keyboardType="email-address"
            autoCapitalize="none"
          />

          <TextInput
            label="Address"
            value={formData.address}
            onChangeText={text => setFormData({ ...formData, address: text })}
            mode="outlined"
            style={styles.input}
            multiline
            numberOfLines={3}
          />

          <TextInput
            label="Medical History"
            value={formData.medicalHistory}
            onChangeText={text => setFormData({ ...formData, medicalHistory: text })}
            mode="outlined"
            style={styles.input}
            multiline
            numberOfLines={3}
          />

          <TextInput
            label="Allergies"
            value={formData.allergies}
            onChangeText={text => setFormData({ ...formData, allergies: text })}
            mode="outlined"
            style={styles.input}
            multiline
            numberOfLines={2}
          />

          <TextInput
            label="Current Medications"
            value={formData.currentMedications}
            onChangeText={text => setFormData({ ...formData, currentMedications: text })}
            mode="outlined"
            style={styles.input}
            multiline
            numberOfLines={2}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Button
            mode="contained"
            onPress={handleSubmit}
            style={styles.button}
            loading={loading}
            disabled={loading}
          >
            Add Patient
          </Button>
        </Surface>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  surface: {
    padding: 16,
    borderRadius: 8,
    elevation: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 24,
    textAlign: 'center',
  },
  input: {
    marginBottom: 16,
  },
  label: {
    fontSize: 16,
    marginBottom: 8,
  },
  segmentedButtons: {
    marginBottom: 16,
  },
  button: {
    marginTop: 8,
    paddingVertical: 8,
  },
  error: {
    color: 'red',
    marginBottom: 16,
    textAlign: 'center',
  },
});

export default AddPatientScreen; 