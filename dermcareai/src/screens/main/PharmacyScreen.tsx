import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { Button, Card, Divider, Surface, Text, TextInput } from 'react-native-paper';
import { StockItem, clinicApi } from '../../services/clinicApi';

const PharmacyScreen: React.FC = () => {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [medicineId, setMedicineId] = useState('');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('10');
  const [patientId, setPatientId] = useState('');
  const [message, setMessage] = useState('');

  const load = async () => {
    try { setStock(await clinicApi.listStock()); } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to load stock'); }
  };
  useEffect(() => { void load(); }, []);

  const addStockReceipt = async () => {
    try {
      await clinicApi.addStock({ medicine_id: medicineId.trim(), name: name.trim(), quantity: Number(quantity) || 0, reorder_level: 5 });
      setMessage('Stock receipt saved.');
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to save stock'); }
  };

  const dispenseFirst = async (item: StockItem) => {
    if (!patientId.trim()) { setMessage('Enter patient ID before dispensing.'); return; }
    try {
      await clinicApi.dispense({ patient_id: patientId.trim(), items: [{ medicine_id: item.medicine_id, quantity: 1 }] });
      setMessage(`${item.name || item.medicine_id}: 1 unit dispensed.`);
      await load();
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to dispense'); }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Surface style={styles.surface}>
        <Text variant="headlineSmall">Pharmacy</Text>
        <TextInput label="Medicine ID" value={medicineId} onChangeText={setMedicineId} style={styles.input} />
        <TextInput label="Medicine name" value={name} onChangeText={setName} style={styles.input} />
        <TextInput label="Quantity to add" value={quantity} onChangeText={setQuantity} keyboardType="decimal-pad" style={styles.input} />
        <Button mode="contained" onPress={addStockReceipt}>Add stock receipt</Button>
        <Divider style={styles.divider} />
        <TextInput label="Patient ID for dispensing" value={patientId} onChangeText={setPatientId} style={styles.input} />
        {stock.map(item => {
          const low = Number(item.quantity) <= Number(item.reorder_level ?? 0);
          return <Card key={item.medicine_id} style={styles.card}><Card.Content><Text variant="titleMedium">{item.name || item.medicine_id}</Text><Text>Stock: {item.quantity} {low ? ' • LOW STOCK' : ''}</Text>{item.batch ? <Text>Batch: {item.batch}</Text> : null}{item.expiry ? <Text>Expiry: {item.expiry}</Text> : null}<Button mode="outlined" onPress={() => dispenseFirst(item)} style={styles.action}>Dispense 1</Button></Card.Content></Card>;
        })}
        {!!message && <Text style={styles.message}>{message}</Text>}
      </Surface>
    </ScrollView>
  );
};

const styles = StyleSheet.create({ container: { padding: 16 }, surface: { padding: 16, borderRadius: 12 }, input: { marginVertical: 6 }, divider: { marginVertical: 18 }, card: { marginVertical: 6 }, action: { marginTop: 10 }, message: { marginTop: 12 } });
export default PharmacyScreen;
