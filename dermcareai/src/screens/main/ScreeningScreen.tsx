import React, { useEffect, useState } from 'react';
import { Alert, Image, ScrollView, StyleSheet, View } from 'react-native';
import { ActivityIndicator, Button, Card, Searchbar, Surface, Text, useTheme } from 'react-native-paper';
import * as ImagePicker from 'expo-image-picker';
import { Camera } from 'expo-camera';
import { collection, addDoc, getDocs, query, where } from 'firebase/firestore';
import { auth, db } from '../../config/firebase';
import { useIsFocused } from '@react-navigation/native';
import { NavigationProps, Patient, ScreeningReport } from '../../navigation/types';
import { ABSTAIN_LABEL, api, PredictionResponse } from '../../services/api';

const ScreeningScreen: React.FC<NavigationProps<'Screening'>> = ({ navigation, route }) => {
  const theme = useTheme();
  const isFocused = useIsFocused();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(route?.params?.patient || null);
  const [image, setImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void fetchPatients();
  }, []);

  useEffect(() => {
    if (isFocused && route?.params?.patient) {
      setSelectedPatient(route.params.patient);
    }
  }, [isFocused, route?.params?.patient]);

  const fetchPatients = async () => {
    const userId = auth.currentUser?.uid;
    if (!userId) return;
    try {
      const snapshot = await getDocs(query(collection(db, 'patients'), where('doctorId', '==', userId)));
      setPatients(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }) as Patient));
    } catch (error) {
      console.error('Patient loading failed', error);
      Alert.alert('Error', 'Unable to load patients.');
    }
  };

  const requestPermissions = async () => {
    const camera = await Camera.requestCameraPermissionsAsync();
    const media = await ImagePicker.requestMediaLibraryPermissionsAsync();
    return camera.status === 'granted' && media.status === 'granted';
  };

  const captureOrPick = async (mode: 'camera' | 'library') => {
    if (!selectedPatient) {
      Alert.alert('Select patient', 'Please select a patient before screening.');
      return;
    }
    if (!(await requestPermissions())) {
      Alert.alert('Permission required', 'Camera and photo-library permissions are required for screening.');
      return;
    }

    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 1,
      allowsEditing: true,
    };
    const picker = mode === 'camera'
      ? await ImagePicker.launchCameraAsync(options)
      : await ImagePicker.launchImageLibraryAsync(options);

    if (!picker.canceled && picker.assets[0]?.uri) {
      const uri = picker.assets[0].uri;
      setImage(uri);
      await analyze(uri);
    }
  };

  const analyze = async (uri: string) => {
    setLoading(true);
    setResult(null);
    setProcessedImage(null);
    try {
      const prediction = await api.analyzeSkinImage(uri);
      setResult(prediction);
      if (prediction.visualization) {
        setProcessedImage(`data:image/jpeg;base64,${prediction.visualization}`);
      }

      const message = prediction.accepted
        ? `${prediction.class_name} • ${(prediction.confidence * 100).toFixed(1)}% confidence`
        : `${ABSTAIN_LABEL}\n${prediction.safety_reason}`;
      Alert.alert('AI screening result', message);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Analysis failed.';
      Alert.alert('AI screening unavailable', message);
    } finally {
      setLoading(false);
    }
  };

  const saveReport = async () => {
    if (!selectedPatient || !image || !result) return;
    const userId = auth.currentUser?.uid;
    if (!userId) return;

    const recommendations = api.getRecommendations(result.class_name);
    const reportData: Omit<ScreeningReport, 'id'> = {
      patientId: selectedPatient.id,
      patientName: selectedPatient.name,
      date: new Date().toISOString(),
      imageUrl: image,
      processedImageUrl: processedImage || '',
      condition: result.class_name,
      confidence: result.confidence,
      model: result.model_used,
      recommendations,
      doctorNotes: '',
    };

    try {
      const ref = await addDoc(collection(db, 'screeningReports'), {
        ...reportData,
        doctorId: userId,
        aiAccepted: result.accepted,
        safetyReason: result.safety_reason,
        appVersion: result.app_version,
        imageQuality: result.image_quality,
      });
      navigation.navigate('ScreeningReport', { report: { id: ref.id, ...reportData } });
    } catch (error) {
      console.error('Report save failed', error);
      Alert.alert('Error', 'Unable to save the screening report.');
    }
  };

  const filteredPatients = patients.filter(patient => patient.name.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.surface}>
        <Text variant="headlineSmall" style={styles.title}>Skin Condition Screening</Text>
        <Card style={styles.warningCard}>
          <Card.Content>
            <Text style={styles.warning}>AI decision-support only. The system can abstain and does not establish a diagnosis.</Text>
          </Card.Content>
        </Card>

        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleMedium">Select Patient</Text>
            <Searchbar placeholder="Search patients" value={searchQuery} onChangeText={setSearchQuery} style={styles.search} />
            {filteredPatients.slice(0, 20).map(patient => (
              <Button key={patient.id} mode={selectedPatient?.id === patient.id ? 'contained' : 'outlined'} onPress={() => setSelectedPatient(patient)} style={styles.patientButton}>
                {patient.name}
              </Button>
            ))}
          </Card.Content>
        </Card>

        {selectedPatient && (
          <>
            <View style={styles.actions}>
              <Button mode="contained" icon="camera" onPress={() => void captureOrPick('camera')} disabled={loading} style={styles.actionButton}>Take Photo</Button>
              <Button mode="outlined" icon="image" onPress={() => void captureOrPick('library')} disabled={loading} style={styles.actionButton}>Choose Image</Button>
            </View>

            {image && <Card style={styles.card}><Card.Content><Text variant="titleMedium">Source Image</Text><Image source={{ uri: image }} style={styles.image} /></Card.Content></Card>}
            {processedImage && <Card style={styles.card}><Card.Content><Text variant="titleMedium">AI Focus Map</Text><Image source={{ uri: processedImage }} style={styles.image} /><Text style={styles.caption}>Focus maps are explanatory aids, not diagnostic evidence.</Text></Card.Content></Card>}

            {loading && <View style={styles.loading}><ActivityIndicator size="large" color={theme.colors.primary} /><Text style={styles.caption}>Running automated evaluation and safety checks…</Text></View>}

            {result && (
              <Card style={styles.card}>
                <Card.Content>
                  <Text variant="titleLarge">AI Result</Text>
                  <Text style={result.accepted ? styles.accepted : styles.abstain}>{result.class_name}</Text>
                  <Text>Confidence: {(result.confidence * 100).toFixed(1)}%</Text>
                  <Text>Model: {result.model_used}</Text>
                  <Text>Safety gate: {result.accepted ? 'PASSED — clinician review required' : 'ABSTAINED'}</Text>
                  <Text style={styles.caption}>{result.safety_reason}</Text>
                  <Text style={styles.caption}>Image quality: {result.image_quality.usable ? 'acceptable' : 'insufficient'} ({result.image_quality.reason})</Text>
                  <Button mode="contained" onPress={() => void saveReport()} style={styles.saveButton}>Save for Clinician Review</Button>
                </Card.Content>
              </Card>
            )}
          </>
        )}
      </Surface>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  surface: { margin: 12, padding: 14, borderRadius: 12 },
  title: { textAlign: 'center', marginBottom: 14 },
  card: { marginVertical: 8 },
  warningCard: { marginBottom: 8 },
  warning: { fontWeight: '700' },
  search: { marginVertical: 10 },
  patientButton: { marginTop: 6 },
  actions: { flexDirection: 'row', gap: 8, marginVertical: 8 },
  actionButton: { flex: 1 },
  image: { width: '100%', height: 300, marginTop: 10, borderRadius: 8, resizeMode: 'cover' },
  loading: { alignItems: 'center', paddingVertical: 24 },
  accepted: { fontSize: 20, fontWeight: '700', marginTop: 8 },
  abstain: { fontSize: 20, fontWeight: '700', marginTop: 8 },
  caption: { marginTop: 8, opacity: 0.75 },
  saveButton: { marginTop: 14 },
});

export default ScreeningScreen;
