import React, { useState } from 'react';
import { View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { TextInput, Button, Text, Surface } from 'react-native-paper';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { auth, db } from '../../config/firebase';
import { createUserWithEmailAndPassword, AuthError } from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';
import { RootStackParamList } from '../../navigation/types';
import { clinicApi } from '../../services/clinicApi';

type RegisterScreenNavigationProp = NativeStackNavigationProp<RootStackParamList, 'Register'>;
interface RegisterScreenProps { navigation: RegisterScreenNavigationProp; }
interface FormData { email: string; password: string; confirmPassword: string; fullName: string; licenseNumber: string; specialization: string; phoneNumber: string; }
interface DoctorData { fullName: string; email: string; licenseNumber: string; specialization: string; phoneNumber: string; createdAt: string; }

const RegisterScreen: React.FC<RegisterScreenProps> = ({ navigation }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<FormData>({ email: '', password: '', confirmPassword: '', fullName: '', licenseNumber: '', specialization: '', phoneNumber: '' });
  const [error, setError] = useState('');

  const handleSignUp = async (): Promise<void> => {
    try {
      setLoading(true); setError('');
      if (!formData.email || !formData.password || !formData.fullName || !formData.licenseNumber || !formData.specialization || !formData.phoneNumber) throw new Error('Please fill in all fields');
      if (formData.password !== formData.confirmPassword) throw new Error('Passwords do not match');
      const userCredential = await createUserWithEmailAndPassword(auth, formData.email, formData.password);
      const doctorData: DoctorData = { fullName: formData.fullName, email: formData.email, licenseNumber: formData.licenseNumber, specialization: formData.specialization, phoneNumber: formData.phoneNumber, createdAt: new Date().toISOString() };
      await setDoc(doc(db, 'doctors', userCredential.user.uid), doctorData);
      await clinicApi.audit({ actor_id: userCredential.user.uid, actor_role: 'doctor', action: 'doctor_registered', resource_type: 'doctor', resource_id: userCredential.user.uid, metadata: { specialization: formData.specialization } }).catch(() => undefined);
      await clinicApi.sendRegistrationNotification({ patient_name: formData.fullName, phone: formData.phoneNumber, appointment_text: 'Your DermCareAI clinic account has been registered successfully.', channels: ['whatsapp', 'sms'] }).catch(() => undefined);
      setFormData({ email: '', password: '', confirmPassword: '', fullName: '', licenseNumber: '', specialization: '', phoneNumber: '' });
      alert('Registration successful! A confirmation notification was requested.');
      navigation.replace('MainTabs');
    } catch (err) {
      const error = err as Error | AuthError;
      setError(error.message);
    } finally { setLoading(false); }
  };

  return <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.container}>
    <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
      <Surface style={styles.surface}>
        <Text style={styles.title}>Create Account</Text><Text style={styles.subtitle}>Join DermCareAI Today</Text>
        <TextInput label="Full Name" value={formData.fullName} onChangeText={(text) => setFormData({ ...formData, fullName: text })} style={styles.input} />
        <TextInput label="Email" value={formData.email} onChangeText={(text) => setFormData({ ...formData, email: text })} keyboardType="email-address" autoCapitalize="none" style={styles.input} />
        <TextInput label="License Number" value={formData.licenseNumber} onChangeText={(text) => setFormData({ ...formData, licenseNumber: text })} style={styles.input} />
        <TextInput label="Specialization" value={formData.specialization} onChangeText={(text) => setFormData({ ...formData, specialization: text })} style={styles.input} />
        <TextInput label="Phone Number" value={formData.phoneNumber} onChangeText={(text) => setFormData({ ...formData, phoneNumber: text })} keyboardType="phone-pad" style={styles.input} />
        <TextInput label="Password" value={formData.password} onChangeText={(text) => setFormData({ ...formData, password: text })} secureTextEntry style={styles.input} />
        <TextInput label="Confirm Password" value={formData.confirmPassword} onChangeText={(text) => setFormData({ ...formData, confirmPassword: text })} secureTextEntry style={styles.input} />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Button mode="contained" onPress={handleSignUp} loading={loading} disabled={loading} style={styles.button}>Sign Up</Button>
        <Button mode="text" onPress={() => navigation.navigate('Login')} style={styles.button}>Already have an account? Login</Button>
      </Surface>
    </ScrollView>
  </KeyboardAvoidingView>;
};

const styles = StyleSheet.create({ container: { flex: 1 }, scrollContent: { flexGrow: 1, justifyContent: 'center', padding: 20 }, surface: { padding: 20, borderRadius: 10, elevation: 4 }, title: { fontSize: 24, fontWeight: 'bold', textAlign: 'center', marginBottom: 8 }, subtitle: { fontSize: 16, textAlign: 'center', marginBottom: 24, opacity: 0.7 }, input: { marginBottom: 16 }, button: { marginTop: 8, paddingVertical: 8 }, error: { color: 'red', marginBottom: 16, textAlign: 'center' } });
export default RegisterScreen;
