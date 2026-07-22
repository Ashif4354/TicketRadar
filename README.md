# TicketRadar 🍿

TicketRadar is a fully asynchronous movie ticket booking monitor and alert system. It continuously watches movie booking pages and alerts you when booking opens for a specific date and theatre list.

> [!NOTE]
> TicketRadar only supports BookMyShow for now. Support for additional ticket booking services and platforms will be implemented in the future.

It features a modern dark-mode web dashboard built with **React** and **FastAPI**, uses **HTTPX** and **BeautifulSoup4** for lightweight, non-blocking browserless HTML scraping, and supports notifications via **Gmail SMTP** or **Discord Webhooks**. The application is secured with **Firebase Authentication**, **App Check**, and Google **reCAPTCHA v2**.

---

## 🌟 Key Features

1. **Fully Asynchronous Execution**: All monitoring checkers run concurrently as non-blocking coroutines on a dedicated background event loop running in a daemon thread.
2. **Fast & Lightweight Scraper**: Uses HTTPX and BeautifulSoup4 for efficient HTML scraping, removing the overhead of heavy headful/headless browser environments.
3. **Real-time Live Dashboard**: React frontend communicates with the FastAPI backend via long-polling, ensuring status updates and real-time logs are shown instantly without spamming the backend or requiring full page refreshes.
4. **Secure User Authentication**: Integrated with Firebase Authentication (supports login/signup) and an access-request approval workflow, secured with Google reCAPTCHA v2 and Firebase App Check.
5. **Movie Name Auto-Extraction**: Automatically extracts the movie name from the page DOM using XPath/CSS class matching, falling back to URL slug parsing if DOM elements are not found.
6. **Table-Formatted Alerts**:
   - **SMTP Email**: Renders a styled HTML table showing the available and unavailable theatres side-by-side.
   - **Discord Webhook**: Compiles a clean, monospace ASCII-art grid table showing theatre availability.
7. **Polite Log Output**: Strictly adheres to a "no-please" policy in all user interfaces, alerts, logs, and messages.

---

## ⚙️ Setup and Installation

### 1. Configure Environment Variables
Copy `src/Backend/.env.example` to `src/Backend/.env`:
```bash
cp src/Backend/.env.example src/Backend/.env
```

### 2. Run the Dashboard
Ensure `uv` and `node` (v18+) are installed, then run the installation and startup commands:
```bash
cp src/UI/.env.example src/UI/.env
make install
make run
```
If `make` is not installed on your system, you can run them manually:
```bash
# Terminal 1: Run the React frontend
cd src/UI && npm install && npm run dev

# Terminal 2: Run the FastAPI backend
cd src/Backend && uv sync
cd src/Backend && uv run python main.py
```
*Note: The backend runs without automatically opening the browser to prevent repeated tab popups during hot-reload development.*

---

## 🖥️ Using the Dashboard

1. **Sign In / Request Access**: Create an account or sign in via the Firebase Auth screen. If your account is new, submit an access request (secured with reCAPTCHA v2) and wait for admin approval.
2. **Verify Connection**: Expand the **📬 Test Alerts Connection** panel in the dashboard to verify your email or webhook configurations immediately.
3. **Register a Monitor**:
   - Paste the BookMyShow Movie Page URL.
   - Select your target date from the date picker.
   - Enter your target theatre names in the text area (**one theatre per line**). Substring matching is supported and is case-sensitive.
   - Choose the alert channel (Email or Discord Webhook).
   - Click **Start Radar**.
4. **Control Monitors**: You can Pause, Restart, or Delete monitors at any time. Click **View logs** on any card to see real-time log output streamed instantly via long polling.

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).
