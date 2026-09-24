import React, { useEffect, useState } from 'react';
import { AppState } from 'react-native';
import { Provider as PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Snackbar } from 'react-native-paper';
import { theme } from './src/theme';
import AppNavigator from './src/navigation/AppNavigator';
import { api } from './src/services/api';

export default function App() {
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  useEffect(() => {
    const flush = async () => {
      const result = await api.flushClinicalSyncQueue();
      if (result.conflicts > 0) {
        setSyncNotice(`${result.conflicts} clinical change(s) require review before synchronization can continue.`);
      } else if (result.exhausted > 0) {
        setSyncNotice(`${result.exhausted} clinical change(s) reached the retry limit and require manual review.`);
      } else if (result.remaining > 0) {
        setSyncNotice(`${result.remaining} clinical change(s) remain queued for synchronization.`);
      }
    };
    void flush();
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
        <Snackbar visible={Boolean(syncNotice)} onDismiss={() => setSyncNotice(null)} duration={7000}>
          {syncNotice || ''}
        </Snackbar>
      </PaperProvider>
    </SafeAreaProvider>
  );
} 