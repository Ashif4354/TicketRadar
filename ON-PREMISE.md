# TicketRadar — On-Premise & Self-Hosting Guide

This comprehensive guide details everything needed to self-host and run TicketRadar on your own infrastructure or local workstation.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
   - [1. Clone Repository](#1-clone-repository)
   - [2. Firebase Configuration](#2-firebase-configuration)
   - [3. Backend Installation](#3-backend-installation)
   - [4. Frontend Installation](#4-frontend-installation)
3. [Environment Configuration](#environment-configuration)
   - [Required Variables (Always)](#required-variables-always)
   - [Optional: Self-Hosted Mode (`DISABLE_PAYMENTS` & `VITE_DISABLE_PAYMENTS`)](#optional-self-hosted-mode-disable_payments--vite_disable_payments)
   - [Optional: Cashfree Payment Gateway](#optional-cashfree-payment-gateway)
   - [Optional: WhatsApp Template Setup](#optional-whatsapp-template-setup)
4. [Twilio Setup (Single Phone Number)](#twilio-setup-single-phone-number)
   - [Purchasing a Number](#purchasing-a-number)
   - [Enabling SMS & Voice](#enabling-sms--voice)
   - [Enabling WhatsApp Business API](#enabling-whatsapp-business-api)
   - [Configuring Webhook Status Callbacks](#configuring-webhook-status-callbacks)
5. [Cashfree PG Setup (Commercial Mode)](#cashfree-pg-setup-commercial-mode)
6. [Required Firestore Composite Indexes](#required-firestore-composite-indexes)
7. [Upgrading & Maintenance](#upgrading--maintenance)
8. [Troubleshooting & Diagnostics](#troubleshooting--diagnostics)

---

## Prerequisites

- **Python 3.12+ / 3.14+** with `uv` package manager (`pip install uv`)
- **Node.js 20+** and `npm`
- **Google Cloud / Firebase Project** with Firestore (Native Mode) and Firebase Authentication enabled
- **Twilio Account** with at least one active phone number (`TWILIO_PHONE_NUMBER`)
- *(Optional)* **Cashfree Merchant Account** (only required if running with `DISABLE_PAYMENTS=false`)

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Ashif4354/TicketRadar.git
cd TicketRadar
```

### 2. Firebase Configuration
1. Go to the [Firebase Console](https://console.firebase.google.com) and create a project.
2. Enable **Firestore Database** in Native mode.
3. Enable **Authentication** and activate the **Google** sign-in provider.
4. Go to **Project Settings → Service Accounts** and generate a new private key JSON.
5. Extract the credentials for your `.env` configuration (see below).

### 3. Backend Installation
```bash
cd src/Backend
cp .env.example .env

# Install backend dependencies with uv
uv sync

# Run database & health verification tests
uv run pytest tests/ -v

# Start FastAPI backend server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Frontend Installation
```bash
cd ../UI
cp .env.example .env

# For free self-hosted mode (optional):
# Set VITE_DISABLE_PAYMENTS=true in src/UI/.env

# Install dependencies and build
npm install
npm run build

# Run local development Vite server
npm run dev
```

---

## Environment Configuration

Create a `.env` file in `src/Backend/` based on `src/Backend/.env.example`.

### Required Variables (Always)
```dotenv
# SMTP Outbound Email Alerts
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Firebase Admin SDK Credentials
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvgI...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=1234567890
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# Telecom Notification Provider
NOTIFICATION_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+919876543210
APP_BASE_URL=https://your-domain.com
```

### Optional: Self-Hosted Mode (`DISABLE_PAYMENTS` & `VITE_DISABLE_PAYMENTS`)

TicketRadar has a first-class self-hosted mode toggled via `DISABLE_PAYMENTS` in the backend and `VITE_DISABLE_PAYMENTS` in the frontend:

- **Backend (`src/Backend/.env`)**: Set `DISABLE_PAYMENTS=true`. The backend reports this setting via `/api/config` and `/api/profile`, bypasses payment deductions during job creation, and rejects payment/wallet endpoints with a `503 Service Unavailable` response.
- **Frontend (`src/UI/.env`)**: Set `VITE_DISABLE_PAYMENTS=true`. When either `VITE_DISABLE_PAYMENTS === 'true'` OR the backend `config.disable_payments === true`:
  - The wallet balance widget, top-up modal, and immutable transaction ledger are hidden in the Profile and Dashboard.
  - Job creation payment step and Cashfree checkout options are bypassed/hidden, defaulting all alerts to free submission.
  - Pricing display reflects free alerts (`Free (Self-Hosted Mode)`).
  - Admin Pricing Schedule, User Wallets, and Cashfree Refunds tabs and management panels are completely hidden.

| Backend (`DISABLE_PAYMENTS`) | Frontend (`VITE_DISABLE_PAYMENTS`) | Mode | Behavior |
|---|---|---|---|
| `true` | `true` | **Free Self-Hosted Mode** | All notification mediums (Email, Discord, SMS, WhatsApp, Voice Calls) are free for all users. The wallet tab, balance widgets, top-ups, pricing configs, and payment gates are completely hidden across the UI and skipped in the API. No Cashfree credentials needed. |
| `false` | `false` | **Commercial Service Mode** | Wallet, pricing schedules, Cashfree PG integration, and atomic credit transactions are strictly enforced. SMS, WhatsApp, and Voice calls require user wallet balance or Cashfree checkout. |

### Optional: Approval Bypass (`DISABLE_APPROVAL` & `VITE_DISABLE_APPROVAL`)

For internal private deployments or single-operator installations where access approvals and waiting lists are not required:
- **Backend (`src/Backend/.env`)**: Set `DISABLE_APPROVAL=true`. The authentication middleware automatically bypasses user authorization checks and clears blocked account restrictions, giving authenticated users immediate access to `/app`.
- **Frontend (`src/UI/.env`)**: Set `VITE_DISABLE_APPROVAL=true`. Automatically redirects authenticated users straight to `/app` instead of the `/unauthorized` waiting screen.

```dotenv
# Bypass user access requests & account authorization
DISABLE_APPROVAL=true
```

### Optional: Cashfree Payment Gateway
*(Only needed if `DISABLE_PAYMENTS=false`)*
```dotenv
DISABLE_PAYMENTS=false
PAYMENT_GATEWAY=cashfree
CASHFREE_APP_ID=your_cf_app_id
CASHFREE_SECRET_KEY=your_cf_secret_key
CASHFREE_ENVIRONMENT=sandbox       # Use 'production' for live payments
CASHFREE_WEBHOOK_SECRET=            # Leave empty; automatically defaults to CASHFREE_SECRET_KEY
CURRENT_TERMS_VERSION=v2.0
```

### Optional: WhatsApp Template Setup
```dotenv
TWILIO_WHATSAPP_CONTENT_SID=HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Notification Architecture & Multi-Medium Templates

TicketRadar features a unified notification template catalog under `src/Backend/lib/services/notification/templates/`:

1. **Email Templates (`EmailTemplates`)**:
   - `signup`: Branded onboarding email sent upon initial registration.
   - `payment_success` & `payment_failed`: Gateway payment receipts with order IDs and amounts.
   - `call_3x_unanswered`: Dispatched when an automated voice call is attempted 3 times without answer, noting the exact phone number dialed, cinema, and alert metadata.
   - `call_success`: Confirms completed voice alert notification with duration and number called.
   - `wallet_topup_success` & `wallet_topup_failed`: Real-time balance addition updates.
   - `wallet_debit` & `wallet_credit`: Granular transaction receipts for alert bookings or admin adjustments.
   - `refund`: Instant refund notice detailing the refund ID, reason, and returned amount.
   - `admin_pricing_changed`: Alerts administrators whenever pricing schedules are updated.
   - `job_created` & `job_cancelled`: Alert job lifecycle updates.
   - `notification_sent` & `notification_failed`: Delivery audit confirmations.
   - `access_granted`: Sent when an administrator approves access for a user.

2. **Message Templates (`MessageTemplates`)**:
   - Centralized concise templates for SMS and WhatsApp (alerts, call retries, wallet topups, debits, refunds).

3. **Discord Templates (`DiscordTemplates`)**:
   - Rich embed structures with ASCII theatre availability tables and quick booking links.

4. **Strategy Pattern Inheritance**:
   - `EmailNotificationStrategy`, `SMSNotificationStrategy`, `WhatsAppNotificationStrategy`, `DiscordWebhookNotificationStrategy`, and `PhoneCallNotificationStrategy` inherit directly from their respective template catalogs and invoke `self.get_template(...)`.

---

## Dynamic Pricing & Medium Management

TicketRadar supports granular per-medium pricing schedules configurable by administrators:
- **Supported Mediums**: SMS (`sms_paise`), WhatsApp (`whatsapp_paise`), Phone Call (`phone_call_paise`), Email (`email_paise`), and Discord (`discord_paise`).
- **Default Pricing**: Email and Discord default to **0 paise (Free)**.
- **Dynamic Pricing Page (`/pricing`)**: Live prices fetched dynamically from `/api/payments/prices`. Any medium set to 0 paise displays a **Free** badge and requires no wallet balance or checkout during alert creation.
- **Audit Logging**: Any price update requires a mandatory audit note, logged immutably to Firestore.

---

## Consent Tracking & Bot Protection

TicketRadar enforces explicit user consent for outbound messaging:
- **Consents**: Users must explicitly opt-in for SMS, WhatsApp, Email, and Discord alerts in `/profile` or during job creation.
- **reCAPTCHA Enforcement**: Google reCAPTCHA v2 verification is enforced when saving contact details, toggling consent opt-in, dispatching test notifications, and creating ticket alerts.
- **Custom Alert Mediums**: Profile settings allow configuring a custom notification email address (with a 1-click "Reset to primary email" option) and custom Discord webhook URL.

---

## Wallet Ledger & Transaction Auditing

- **Rupee Currency Standardization**: The system exclusively uses Indian Rupees (`₹`), completely retiring "credits" terminology.
- **Topup Presets**: Pre-configured quick-selection buttons for **₹5, ₹10, ₹25, and ₹50** with a default preset of ₹10.
- **Global Transaction Ledger**: Administrators can access `GET /admin/transactions` and the dedicated **Transactions** tab in `/admin` to filter, search, and audit wallet events across all users by UID, transaction type (`TOPUP`, `ALERT_DEBIT`, `ADMIN_ADJUSTMENT`, `REFUND`), direction (`CREDIT`, `DEBIT`), and metadata.

---

## Twilio Setup (Single Phone Number)

TicketRadar uses **one dedicated Twilio phone number** (`TWILIO_PHONE_NUMBER`) for all outbound SMS, WhatsApp messages, and Voice calls.

### Purchasing a Number
1. In the [Twilio Console](https://console.twilio.com), navigate to **Phone Numbers → Manage → Buy a number**.
2. Select a number with SMS, Voice, and MMS capabilities (Indian `+91` or international).
3. Set the acquired number as `TWILIO_PHONE_NUMBER=+91XXXXXXXXXX`.

### Enabling SMS & Voice
- Programmable Messaging (SMS) and Programmable Voice are enabled by default on all purchased Twilio numbers.
- Automated calls use Amazon Polly Indian English voice synthesis (`Polly.Aditi`).

### Enabling WhatsApp Business API
1. Navigate to **Twilio Console → Messaging → Senders → WhatsApp senders**.
2. Register your Twilio number with Meta WhatsApp Business.
3. In the [Content Template Builder](https://console.twilio.com/us1/develop/sms/content-template-builder), create a Utility template:
   - Body: `🎬 TicketRadar Alert! Booking is now open for *{{1}}* on *{{2}}*. Book tickets now: {{3}}`
4. Once approved by Meta, copy the Content SID into `TWILIO_WHATSAPP_CONTENT_SID`.
5. *Development Sandbox:* For testing prior to template approval, use the Twilio WhatsApp Sandbox (`join <keyword>`).

### Configuring Webhook Status Callbacks
Twilio dispatches asynchronous delivery receipts and call completion states to TicketRadar:

- **Voice Status Callback:** `https://your-domain.com/api/twilio/call-status`
- **Message Status Callback:** `https://your-domain.com/api/twilio/message-status`

*Local Development Tunnel:* If running on `localhost:8000`, expose using Cloudflare Tunnel or ngrok:
```bash
npx ngrok http 8000
```
Then configure the HTTPS forwarding URL in **Twilio Console → Active Numbers → [Your Number] → Webhooks**.

---

## Cashfree PG Setup (Commercial Mode)

When `DISABLE_PAYMENTS=false`:
1. Register at the [Cashfree Merchant Portal](https://merchant.cashfree.com).
2. Complete merchant onboarding and KYB verification.
3. Obtain API Keys from **Developers → API Keys** (App ID & Secret Key).
4. Configure the Webhook Endpoint in the Cashfree Dashboard:
   - URL: `https://your-domain.com/api/cashfree/webhook`
5. Leave `CASHFREE_WEBHOOK_SECRET=` empty in `.env` (Cashfree signs webhooks with your `CASHFREE_SECRET_KEY`, which TicketRadar automatically uses as fallback).

---

## Required Firestore Composite Indexes

Ensure the following composite indexes are created in **Firebase Console → Firestore Database → Indexes**:

1. **`jobs`**:
   - `created_by` (Ascending) + `created_at` (Descending)
   - `status` (Ascending) + `created_at` (Descending)
2. **`wallet_transactions`**:
   - `uid` (Ascending) + `created_at` (Descending)
   - `idempotency_key` (Ascending)
3. **`payments`**:
   - `uid` (Ascending) + `created_at` (Descending)
   - `gateway_order_id` (Ascending)
4. **`notification_price_configs`**:
   - `is_current` (Ascending) + `created_at` (Descending)
5. **`admin_audit_logs`**:
   - `created_at` (Descending)
   - `admin_uid` (Ascending) + `created_at` (Descending)
6. **`webhook_events`**:
   - `source` (Ascending) + `processed` (Ascending) + `received_at` (Descending)

---

## Upgrading & Maintenance

When pulling updates from upstream:
```bash
git pull origin main

# Update backend dependencies
cd src/Backend
uv sync
uv run pytest tests/ -v

# Rebuild frontend assets
cd ../UI
npm install
npm run build

# Restart service or supervisor process
```

---

## Troubleshooting & Diagnostics

| Issue | Root Cause | Solution |
|---|---|---|
| **SMS/Calls not updating to Delivered** | Twilio webhook callback URL not reaching server | Check ngrok/domain tunnel; verify status callback URL in Twilio Console |
| **WhatsApp message fails to send** | Missing or unapproved WhatsApp template Content SID | Verify `TWILIO_WHATSAPP_CONTENT_SID` or use Twilio WhatsApp Sandbox for dev |
| **Payment webhooks not crediting wallet** | Webhook signature verification mismatch | Verify `CASHFREE_WEBHOOK_SECRET` matches Cashfree merchant dashboard |
| **"Payment features are disabled" (503)** | `DISABLE_PAYMENTS=true` in backend `.env` or `VITE_DISABLE_PAYMENTS=true` in frontend `.env` | Set `DISABLE_PAYMENTS=false` and `VITE_DISABLE_PAYMENTS=false`, and configure Cashfree credentials |
| **Terms Modal appearing repeatedly** | Terms v2.0 not recorded in user profile | Click "Accept & Continue" in UI or verify Firestore write permissions on `users/{uid}` |
| **Phone number rejected** | Number not under Indian numbering plan (+91) | Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 |
| **Polly.Aditi Voice call synthesis** | Twilio Programmable Voice permissions | Ensure voice calls are enabled for destination geography in Twilio Voice Geo-Permissions |
