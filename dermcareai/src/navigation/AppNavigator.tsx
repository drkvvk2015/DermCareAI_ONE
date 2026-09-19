import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useTheme } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../config/firebase';
import { RootStackParamList } from './types';
import LoginScreen from '../screens/auth/LoginScreen';
import RegisterScreen from '../screens/auth/RegisterScreen';
import DashboardScreen from '../screens/main/DashboardScreen';
import PatientsScreen from '../screens/main/PatientsScreen';
import AppointmentsScreen from '../screens/main/AppointmentsScreen';
import ScreeningScreen from '../screens/main/ScreeningScreen';
import ProfileScreen from '../screens/main/ProfileScreen';
import AddPatientScreen from '../screens/main/AddPatientScreen';
import EditPatientScreen from '../screens/main/EditPatientScreen';
import PatientDetailsScreen from '../screens/main/PatientDetailsScreen';
import NewAppointmentScreen from '../screens/main/NewAppointmentScreen';
import AppointmentDetailsScreen from '../screens/main/AppointmentDetailsScreen';
import EditAppointmentScreen from '../screens/main/EditAppointmentScreen';
import ScreeningReportScreen from '../screens/main/ScreeningReportScreen';
import BillingScreen from '../screens/main/BillingScreen';
import PharmacyScreen from '../screens/main/PharmacyScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

const MainTabs = () => {
  const theme = useTheme();
  const common = { tabBarActiveTintColor: theme.colors.primary, tabBarInactiveTintColor: theme.colors.onSurfaceDisabled, tabBarStyle: { backgroundColor: theme.colors.background, borderTopColor: theme.colors.surface } };
  return (
    <Tab.Navigator screenOptions={common}>
      <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="view-dashboard" size={size} color={color} /> }} />
      <Tab.Screen name="Patients" component={PatientsScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="account-group" size={size} color={color} /> }} />
      <Tab.Screen name="Appointments" component={AppointmentsScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="calendar" size={size} color={color} /> }} />
      <Tab.Screen name="Screening" component={ScreeningScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="camera" size={size} color={color} /> }} />
      <Tab.Screen name="Billing" component={BillingScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="cash-register" size={size} color={color} /> }} />
      <Tab.Screen name="Pharmacy" component={PharmacyScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="pill" size={size} color={color} /> }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarIcon: ({ color, size }) => <Icon name="account" size={size} color={color} /> }} />
    </Tab.Navigator>
  );
};

const AppNavigator = () => {
  const [user, setUser] = useState(auth.currentUser);
  const [initializing, setInitializing] = useState(true);
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, current => { setUser(current); setInitializing(false); });
    return unsubscribe;
  }, []);
  if (initializing) return null;
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {user ? (
          <>
            <Stack.Screen name="MainTabs" component={MainTabs} />
            <Stack.Screen name="AddPatient" component={AddPatientScreen} />
            <Stack.Screen name="EditPatient" component={EditPatientScreen} />
            <Stack.Screen name="PatientDetails" component={PatientDetailsScreen} />
            <Stack.Screen name="NewAppointment" component={NewAppointmentScreen} />
            <Stack.Screen name="AppointmentDetails" component={AppointmentDetailsScreen} />
            <Stack.Screen name="EditAppointment" component={EditAppointmentScreen} />
            <Stack.Screen name="ScreeningReport" component={ScreeningReportScreen} />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Register" component={RegisterScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;
