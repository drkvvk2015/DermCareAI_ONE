# DermCareAI — Dermatology Clinic Operating System

DermCareAI now combines patient/appointment management with AI-assisted lesion screening, billing, UPI checkout, pharmacy inventory/dispensing, durable audit logging, and configurable WhatsApp/SMS notifications.

## AI models

The backend supports the existing DermCareAI research weights and an optional locally cached embedded HAM10000 7-class transformer model (`PREMAADC/vit-base-ham10000`). The embedded model is a research fallback and is **not clinically validated**. The application must not treat model output as a diagnosis or use it as the sole basis for treatment decisions.

Model versions and local weights are represented in `backend/models/registry.json`. Hash verification is exposed by `/models` and the service retains bounded self-healing/reload behaviour.

## Billing and UPI

The mobile app includes billing and invoice creation. Razorpay integration creates hosted payment links; the hosted checkout can provide UPI Intent/QR. Do not implement new UPI Collect flows. Configure Razorpay credentials in `backend/.env.example`.

Razorpay notes that UPI Collect is deprecated for most use cases from 28 February 2026 and recommends UPI Intent or UPI QR for new integrations. See the provider documentation before production launch.

## Pharmacy

The pharmacy module provides medicine master/stock endpoints, batch/expiry fields, reorder thresholds, stock deduction and prescription-linked dispensing. Production deployment should add role-based pharmacy authorization and a persistent transactional database before using it for a live dispensing operation.

## Auditing

`/audit/events` stores timestamped, hash-chained audit events in SQLite. Critical events should be generated for patient changes, prescriptions, dispensing, invoices, payments, notifications, AI screening and administrative actions. For multi-instance production deployments, move the audit store to a managed append-only datastore.

## Notifications

The notification adapter supports:
- WhatsApp Cloud API template messages
- Indian SMS-provider integration using DLT-approved templates
- a privacy-safe social webhook for operational events

Never send diagnoses, prescriptions, payment details, lesion images or other sensitive health information to public social networks. Register and approve message templates/headers and collect consent where required.

## Regulatory and security boundary

This is a healthcare software platform and AI module, not automatically a licensed medical device or pharmacy system. In India, Medical Device Software can fall under the Medical Devices Rules, 2017 and CDSCO guidance; the actual classification depends on intended use and claims. Conduct a formal regulatory/privacy/security assessment before commercialization.

## Configuration

Copy `backend/.env.example` to your deployment environment and provide only server-side secrets. Never commit API keys, access tokens, webhook secrets or patient data to Git.

## Existing mobile features

Patient profiles, appointments, clinical records, prescriptions/notes, screening reports and the continuous evaluation/self-healing infrastructure remain part of the application.
