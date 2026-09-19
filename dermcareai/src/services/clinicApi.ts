import auth from '@react-native-firebase/auth';
import { API_URL } from '@env';

export type InvoiceItem = { description: string; quantity: number; unit_price: number; tax_percent?: number };
export type Invoice = { id: string; patient_id: string; subtotal: number; tax: number; discount: number; total: number; currency: string; status: string };
export type StockItem = { medicine_id: string; name: string; quantity: number; reorder_level?: number; batch?: string; expiry?: string; unit_price?: number };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const user = auth().currentUser;
  const token = user ? await user.getIdToken() : null;
  if (!token) throw new Error('Authentication required. Please sign in again.');
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(init?.headers || {}) } });
  const text = await response.text();
  if (!response.ok) throw new Error(text || `Request failed: ${response.status}`);
  return (text ? JSON.parse(text) : {}) as T;
}

export const clinicApi = {
  createInvoice(payload: { patient_id: string; items: InvoiceItem[]; discount?: number }): Promise<Invoice> {
    return request<Invoice>('/commerce/invoices', { method: 'POST', body: JSON.stringify(payload) });
  },
  createUpiPayment(payload: { invoice_id: string; amount?: number; customer_name: string; customer_phone: string; customer_email?: string }) {
    const { amount: _deprecatedClientAmount, ...serverPayload } = payload;
    return request<{ provider: string; id: string; short_url: string; upi_supported: boolean; amount_paise: number }>('/commerce/payments/razorpay', { method: 'POST', body: JSON.stringify(serverPayload) });
  },
  listStock(): Promise<StockItem[]> {
    return request<StockItem[]>('/commerce/pharmacy/stock');
  },
  addStock(payload: StockItem) {
    return request<StockItem>('/commerce/pharmacy/stock', { method: 'POST', body: JSON.stringify(payload) });
  },
  dispense(payload: { patient_id: string; prescription_id?: string; items: { medicine_id: string; quantity: number }[] }) {
    return request('/commerce/pharmacy/dispense', { method: 'POST', body: JSON.stringify(payload) });
  },
  sendRegistrationNotification(payload: { patient_name: string; phone: string; appointment_text: string; channels: string[] }) {
    return request('/notifications/registration', { method: 'POST', body: JSON.stringify(payload) });
  },
  audit(payload: { action: string; resource_type: string; resource_id: string; metadata?: Record<string, unknown> }) {
    return request('/audit/events', { method: 'POST', body: JSON.stringify(payload) });
  },
};
