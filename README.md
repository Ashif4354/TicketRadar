# TicketRadar 🍿

TicketRadar is a fully asynchronous movie ticket booking monitor and alert system. It continuously watches movie booking pages and alerts you when booking opens for a specific date and theatre list.

> [!NOTE]
> TicketRadar only supports BookMyShow for now. Support for additional ticket booking services and platforms will be implemented in the future.

It features a modern dark-mode web dashboard built with **Streamlit**, uses **Playwright (Async)** for non-blocking browser scraping, and supports notifications via **Gmail SMTP** or **Discord Webhooks**.

---

## 🌟 Key Features

1. **Fully Asynchronous Execution**: All monitoring checkers run concurrently as non-blocking coroutines on a dedicated background event loop running in a daemon thread.
2. **Movie Name Auto-Extraction**: Automatically extracts the movie name from the page DOM using the link xpath matching the URL scheme. It falls back to URL slug parsing if DOM elements are not found.
3. **Table-Formatted Alerts**:
   - **SMTP Email**: Renders a styled HTML table showing the available and unavailable theatres side-by-side.
   - **Discord Webhook**: Compiles a clean, monospace ASCII-art grid table showing theatre availability.
4. **Custom Browser Visibility Options**: Option to run the Playwright browser instance in the background (headless) or in the foreground (visible Chrome window) to observe operations in real time.
5. **Polite Log Output**: Strictly adheres to a "no-please" policy in all user interfaces, alerts, logs, and messages.



## ⚙️ Setup and Installation

### 1. Prerequisite: Google Chrome
TicketRadar launches Google Chrome directly from your system paths using Playwright's `"chrome"` channel. Ensure Google Chrome is installed on your host system.

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the project root:
```bash
cp .env.example .env
```
Open `.env` and fill in your Gmail SMTP configurations (App Password required for 2-step verification accounts):
```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Run the Dashboard
Ensure `uv` is installed, then launch the Streamlit dashboard:
```bash
uv run streamlit run main.py
```

### 📦 Running as a Standalone Executable
You can compile TicketRadar into a standalone executable (`TicketRadar.exe`) to distribute and run it without a local Python setup.

#### How to Build
To compile the executable:
```bash
make build
```
*(If `make` is not installed on your Windows machine, run: `uv run pyinstaller TicketRadar.spec --clean`)*

The output binary will be created at `dist/TicketRadar.exe`.

#### How to Use
1. Copy your `.env` configuration file into the **same directory** as `TicketRadar.exe`.
2. Double-click `TicketRadar.exe` to launch the application.
3. The app will launch a terminal console window, read the `.env` settings, start the local server, and automatically open your default browser to the TicketRadar dashboard.
4. **How to Stop**: Simply close the terminal console window, or press `Ctrl+C` inside the terminal window.

---

## 🖥️ Using the Dashboard

1. **Verify Connection**: Expand the **📬 Test Alerts Connection** panel in the sidebar to verify your email or webhook configurations immediately.
2. **Register a Monitor**:
   - Paste the Movie Page URL.
   - Select your target date from the date picker.
   - Enter your target theatre names in the text area (**one theatre per line**). Substring matching is supported but it is strictly case-sensitive.
   - Choose the alert channel.
   - Check or uncheck **Run browser in background** to show or hide Chrome during checks.
   - Click **Start Radar**.
3. **Control Monitors**: You can Pause, Restart, or Delete monitors at any time. Click **View logs** on any card to see real-time output.

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).


