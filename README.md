# TicketRadar 🍿

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TicketRadar is a fully asynchronous movie ticket booking monitor and alert system. It continuously watches movie booking pages and alerts you in real time as soon as ticket bookings open for your requested date and theatre list.

> [!NOTE]
> TicketRadar currently supports **BookMyShow**. Support for additional ticket booking services and multiplex chains (such as District by Zomato and PVR INOX) will be added in upcoming releases.

---

## 📸 Overview & Key Features

- **⚡ Fully Asynchronous Execution**: All monitoring checkers run concurrently as non-blocking coroutines on a dedicated background event loop in FastAPI.
- **🪶 Lightweight Browserless Scraper**: Uses **HTTPX**, **BeautifulSoup4**, and **curl-cffi** (TLS fingerprint impersonation) for fast, lightweight HTML parsing without heavy headless browser overhead.
- **🖥️ Modern Real-Time Dashboard**: Responsive dark-mode frontend built with **React 19**, **Vite**, and **Tailwind CSS**. Streams live logs and status updates from the FastAPI backend via long-polling.
- **🔒 Secure Authentication & Role Management**: Secured with **Firebase Authentication**, **App Check**, and Google **reCAPTCHA v2**, featuring an access-request approval workflow and an **Admin Control Panel**.
- **🎯 Smart Theatre & Movie Matching**: Auto-extracts movie titles, handles URL date segment rewriting, and performs case-insensitive substring matching on theatre names.
- **📊 Rich Side-by-Side Availability Alerts**:
  - **SMTP Email**: Renders a formatted HTML table displaying available vs. unavailable theatres side-by-side.
  - **Discord Webhook**: Sends a clean monospace ASCII-art grid table showing theatre availability.
- **🧪 Test Alert Connection**: Dedicated UI modal to test SMTP email credentials or Discord webhooks prior to starting a radar.
- **🤫 Polite Output**: Enforces clean, professional logging across all user interfaces, notifications, and logs.

---

## 📁 Directory Structure

```text
TicketRadar/
├── export/                # Build configuration & scripts (Nuitka, PyInstaller)
├── scripts/               # Utility scripts (e.g. set_admin.py)
├── src/
│   ├── Backend/           # FastAPI backend server & monitoring engine
│   │   ├── api/           # API routes (auth, admin, jobs, config)
│   │   ├── lib/           # Scraper, notifier, GCP logger & core job manager
│   │   └── main.py        # FastAPI entry point
│   └── UI/                # React 19 + Vite frontend application
│       └── src/           # Components, pages (Dashboard, Admin, Instructions, etc.)
├── Makefile               # Task automation commands
└── README.md
```

---

## ⚙️ Prerequisites & Setup

### Prerequisites
- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **[uv](https://docs.astral.sh/uv/)** (recommended Python package installer & manager)
- **Firebase Project** (Auth & Firestore enabled)

---

### 1. Configure Environment Variables

#### Backend Configuration (`src/Backend/.env`)
Copy the backend example file:
```bash
cp src/Backend/.env.example src/Backend/.env
```
Fill in your configuration details in `src/Backend/.env`:
- **SMTP Settings**: Gmail / SMTP host (`SMTP_SERVER`), port (`587`), email (`SMTP_EMAIL`), and App Password (`SMTP_PASSWORD`).
- **Firebase Admin SDK**: Firebase project ID and service account credentials (`FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, etc.).
- **reCAPTCHA v2**: Secret key (`RECAPTCHA_SECRET`).
- **Admin Notifications**: Discord Webhook URL for pending access requests (`ADMIN_DISCORD_WEBHOOK_URL`).
- **GCP Logging (Optional)**: Google Cloud Logging credentials (`GCP_LOGGING_PROJECT_ID`, `GCP_LOGGING_PRIVATE_KEY`, etc.) for remote log streaming.

#### Frontend Configuration (`src/UI/.env`)
Copy the frontend example file:
```bash
cp src/UI/.env.example src/UI/.env
```
Fill in your configuration details in `src/UI/.env`:
- **Firebase Web SDK**: `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_PROJECT_ID`, etc.
- **reCAPTCHA & App Check**: `VITE_APP_CHECK_SITE_KEY`, `VITE_RECAPTCHA_V2_SITE_KEY`.
- **Backend Target URL**: `VITE_BACKEND_URL` (default: `http://127.0.0.1:8000`).

---

### 2. Install Dependencies

Install both backend (`uv sync`) and frontend (`npm install`) dependencies in a single step using `make`:
```bash
make install
```
*Or manually:*
```bash
# Install backend dependencies
cd src/Backend && uv sync

# Install frontend dependencies
cd src/UI && npm install
```

---

### 3. Set Up Initial Admin Account

1. **Register User Account**: Launch the app and register/sign up with your email address via the frontend UI (`http://localhost:5173`).
2. **Promote Account to Admin**: Once registered in Firebase Authentication, run the admin promotion script:
```bash
cd src/Backend
uv run python ../../scripts/set_admin.py your-email@example.com
```
This script sets Firebase Custom Claims (`role: admin`, `authorized: true`) for the specified user account to grant access to the Admin Dashboard (`/admin`) and approve pending access requests.

---

### 4. Running for Development

To run TicketRadar in development mode, start both the React frontend dev server and the FastAPI backend server in separate terminal windows:

#### Terminal 1: React Frontend (UI)
```bash
make ui
# Or manually: cd src/UI && npm run dev
```
*The frontend dashboard will be available at `http://localhost:5173`.*

#### Terminal 2: FastAPI Backend
```bash
make run
# Or manually: cd src/Backend && uv sync && uv run python main.py
```
*The API backend will be available at `http://127.0.0.1:8000`.*

---

## 🖥️ Using TicketRadar

1. **Sign In & Access Request**: Open the dashboard at `http://localhost:5173`. Create an account or sign in via Firebase Auth. New users submit an access request which notifies admins.
2. **Verify Alert Configuration**: Expand the **📬 Test Alerts Connection** section to send a test email or Discord notification before launching a radar.
3. **Register a Radar Monitor**:
   - **Booking URL**: Paste the BookMyShow movie showtimes URL (e.g. `https://in.bookmyshow.com/buytickets/...`).
   - **Target Date**: Pick your intended movie date.
   - **Target Theatres**: List theatre names (one per line). Substring matching is case-insensitive.
   - **Check Frequency**: Set interval between checks (1–30 minutes).
   - **Alert Channels**: Select Email or Discord Webhook.
   - Click **Start Radar**.
4. **Manage Monitors & View Live Logs**: Pause, resume, restart, or delete active monitors. Click **View logs** on any monitor card to stream real-time log output via backend long-polling.
5. **Detailed Instructions**: Visit the **Instructions (`/instruction`)** page in the dashboard for step-by-step guidance on capturing URLs and formatting theatre lists for BookMyShow.

---

## 📦 Building & Packaging

TicketRadar supports building production assets and standalone desktop executables.

| Command | Description | Output Location |
| :--- | :--- | :--- |
| `make build-ui` | Compiles the React frontend production bundle | `src/UI/dist` |
| `make build-nuitka` | Builds standalone executable using Nuitka (recommended, fast startup) | `dist/nuitka/TicketRadar.dist/TicketRadar.exe` |
| `make build-pyinstaller` | Builds single-file executable using PyInstaller | `dist/pyinstaller/TicketRadar.exe` |
| `make clean` | Cleans build artifacts (`build/`, `dist/`, `src/UI/dist`) | — |

---

## 🚀 Cloud Deployment

Deploy the FastAPI backend directly to FastAPI Cloud:
```bash
make deploy
# Runs: cd src/Backend && uv run fastapi deploy
```

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).
