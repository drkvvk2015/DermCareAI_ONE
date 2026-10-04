import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from 'react-native-paper';

export default function ClinicalAISafetyBanner() {
  return (
    <View accessibilityRole="text" style={styles.container}>
      <Text variant="labelLarge">Clinical AI Copilot — Suggestions only.</Text>
      <Text variant="bodySmall">Verify all information and make the final clinical decision.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
});
