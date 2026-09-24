import React, { useEffect } from 'react';
import { AppState } from 'react-native';
import { Provider as PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { theme } from './src/theme';
import AppNavigator from './src/navigation/AppNavigator';
import { api } from './src/services/api';

export default function App() {
  useEffect(() => {
    const flush = () => {
      void api.flushClinicalSyncQueue();
    };
    flush();
    const subscription = AppState.addEventListener('change', state => {
      if (state === 'active') flush();
    });
    return () => subscription.remove();
  }, []);

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <AppNavigator />
      </PaperProvider>
    </SafeAreaProvider>
  );
} 