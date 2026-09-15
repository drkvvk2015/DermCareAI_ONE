import React, { useState } from 'react';
import { Linking, ScrollView, StyleSheet } from 'react-native';
import { Button, Card, Surface, Text, TextInput } from 'react-native-paper';
import { clinicApi, Invoice } from '../../services/clinicApi';

const BillingScreen: React.FC = () => {
  const [patientId, setPatientId] = useState('');
  const [description, setDescription] = useState('Consultation');
  const [amount, setAmount] = useState('500');
  const [phone, setPhone] = useState('');
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [message, setMessage] = useState('');

  const createInvoice = async () => {
    try {
      const result = await clinicApi.createInvoice({
        patient_id: patientId.trim() || 'walk-in',
        items: [{ description, quantity: 1, unit_price: Number(amount) || 0, tax_percent: 0 }],
      });
      setInvoice(result);
      setMessage(`Invoice ${result.id} created.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to create invoice');
    }
  };

  const payByUpi = async () => {
    if (!invoice || !phone.trim()) {
      setMessage('Create an invoice and enter the payer mobile number first.');
      return;
    }
    try {
      const result = await clinicApi.createUpiPayment({ invoice_id: invoice.id, amount: Math.round(invoice.total * 100), customer_name: patientId || 'Patient', customer_phone: phone });
      await Linking.openURL(result.short_url);
      setMessage('UPI payment checkout opened.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to start UPI payment');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Surface style={styles.surface}>
        <Text variant="headlineSmall">Billing & UPI</Text>
        <TextInput label="Patient ID" value={patientId} onChangeText={setPatientId} style={styles.input} />
        <TextInput label="Service / item" value={description} onChangeText={setDescription} style={styles.input} />
        <TextInput label="Amount (INR)" value={amount} onChangeText={setAmount} keyboardType="decimal-pad" style={styles.input} />
        <TextInput label="Payer mobile" value={phone} onChangeText={setPhone} keyboardType="phone-pad" style={styles.input} />
        <Button mode="contained" onPress={createInvoice}>Create invoice</Button>
        {invoice && <Card style={styles.card}><Card.Content><Text>{invoice.id}</Text><Text>Total: ₹{invoice.total.toFixed(2)}</Text><Text>Status: {invoice.status}</Text><Button mode="outlined" onPress={payByUpi} style={styles.action}>Pay via UPI</Button></Card.Content></Card>}
        {!!message && <Text style={styles.message}>{message}</Text>}
      </Surface>
    </ScrollView>
  );
};

const styles = StyleSheet.create({ container: { padding: 16 }, surface: { padding: 16, borderRadius: 12 }, input: { marginVertical: 6 }, card: { marginTop: 16 }, action: { marginTop: 12 }, message: { marginTop: 12 } });
export default BillingScreen;
