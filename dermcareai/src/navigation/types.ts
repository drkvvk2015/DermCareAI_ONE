import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';

export type Patient = {
  id: string;
  name: string;
  age: number;
  gender: string;
  phone?: string;
  email?: string;
  address?: string;
  medicalHistory?: string;
  allergies?: string;
  currentMedications?: string;
  upcomingVisit?: string;
};

export interface AIGovernanceCard {
  decision_type: 'clinical_decision_support';
  intended_use: string;
  diagnostic_status: 'not_a_diagnosis';
  human_review_required: boolean;
  abstention_enabled: boolean;
  confidence_threshold: number;
  model_provenance: string;
  model_name: string;
  research_model: boolean;
  safety_controls: string[];
  limitations: string[];
}

export interface ScreeningReport {
  id: string;
  patientId: string;
  patientName: string;
  date: string;
  imageUrl: string;
  processedImageUrl: string;
  condition: string;
  confidence: number;
  model: string;
  recommendations: string[];
  governance?: AIGovernanceCard;
  doctorNotes?: string;
}

export type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled' | 'no-show';
export type Appointment = { id: string; patientId: string; patientName: string; doctorId: string; date: string; time: string; type: string; status: AppointmentStatus; notes?: string; diagnosis?: string; prescription?: string; createdAt: string; updatedAt: string };

export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  MainTabs: undefined;
  AddPatient: undefined;
  EditPatient: { patient: Patient };
  PatientDetails: { patient: Patient };
  NewAppointment: undefined | { patient?: Patient };
  AppointmentDetails: { appointment: Appointment };
  EditAppointment: { appointment: Appointment };
  Screening: undefined | { patient?: Patient };
  ScreeningReport: { report: ScreeningReport };
  Billing: undefined;
  Pharmacy: undefined;
};

export type NavigationProps<T extends keyof RootStackParamList> = {
  navigation: NativeStackNavigationProp<RootStackParamList, T>;
  route: RouteProp<RootStackParamList, T>;
};
