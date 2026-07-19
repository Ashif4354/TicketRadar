# main.py

import streamlit as st
import datetime
import time
import os
import sys
import asyncio

# Ensure the root project directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings, config_error
from src.core.job import MonitorJob
from src.core.monitor import JobManager
from src.ui.styles import inject_premium_styles
from src.ui.components import render_job_card
from src.services.notification.factory import NotificationStrategyFactory

# Configure the Streamlit Page metadata and layout
st.set_page_config(
    page_title="TicketRadar",
    layout="wide",
    page_icon="🍿",
    initial_sidebar_state="expanded"
)

# Inject visual styles
inject_premium_styles()

# Render Gradient Header and Title
st.markdown('<div class="gradient-text">🍿 TicketRadar</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle-text">Continuously watch movie ticket booking availability for a specific date and theatre list, and receive notifications via Email or Discord Webhook.</div>', 
    unsafe_allow_html=True
)

# Catch configuration errors (e.g. missing variables in .env)
if config_error:
    st.error("⚠️ Configuration Validation Error")
    st.markdown(f"**Error Details:**\n```\n{config_error}\n```")
    st.info("Verify that your `.env` file exists and contains all required variables: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_EMAIL`, `SMTP_PASSWORD`.")
    st.stop()

# Get Singleton manager instance
manager = JobManager()

# Sidebar Setup
st.sidebar.markdown("### ⚙️ System Controls")
auto_refresh = st.sidebar.checkbox("Auto Refresh Dashboard (10s) 🔄", value=True)

# Add a manual refresh button
if st.sidebar.button("Force Refresh Now 🔄", use_container_width=True):
    st.rerun()

# Test notification utility panel
with st.sidebar.expander("📬 Test Alerts Connection", expanded=False):
    test_medium = st.selectbox("Alert Type", ["Email", "Discord Webhook"], key="test_medium")
    
    if test_medium == "Email":
        test_email = st.text_input("Test Recipient Email", placeholder="user@gmail.com")
        if st.button("Send Test Email 📨", use_container_width=True):
            if test_email:
                with st.spinner("Sending..."):
                    try:
                        notifier = NotificationStrategyFactory.create_strategy("email", {"recipient_email": test_email})
                        success, msg = asyncio.run(
                            notifier.send_notification(
                                subject="Test Alert",
                                movie_name="Test Movie",
                                date_str="20260719",
                                available_theatres=["Sample Theatre A", "Sample Theatre B"],
                                unavailable_theatres=["Sample Theatre C"],
                                url="https://in.bookmyshow.com"
                            )
                        )
                        if success:
                            st.success("Test email sent!")
                        else:
                            st.error(msg)
                    except Exception as err:
                        st.error(f"Error: {err}")
            else:
                st.warning("Provide a recipient email.")
    else:
        test_webhook = st.text_input("Test Webhook URL", placeholder="https://discord.com/api/webhooks/...")
        if st.button("Send Test Webhook 💬", use_container_width=True):
            if test_webhook:
                with st.spinner("Sending..."):
                    try:
                        notifier = NotificationStrategyFactory.create_strategy("discord", {"webhook_url": test_webhook})
                        success, msg = asyncio.run(
                            notifier.send_notification(
                                subject="Test Alert",
                                movie_name="Test Movie",
                                date_str="20260719",
                                available_theatres=["Sample Theatre A", "Sample Theatre B"],
                                unavailable_theatres=["Sample Theatre C"],
                                url="https://in.bookmyshow.com"
                            )
                        )
                        if success:
                            st.success("Test webhook sent!")
                        else:
                            st.error(msg)
                    except Exception as err:
                        st.error(f"Error: {err}")
            else:
                st.warning("Provide a webhook URL.")

# Split interface layout
col_form, col_monitors = st.columns([1, 2], gap="large")

with col_form:
    st.markdown("### ⚙️ Global Configuration")
    
    service_provider = st.selectbox(
        "Service Provider 🍿",
        ["BookMyShow"],
        key="form_service"
    )
    
    medium = st.selectbox(
        "Notification Medium 📢",
        ["Email", "Discord Webhook"],
        key="form_medium"
    )
    
    # Dynamic inputs based on selected medium
    recipient_email = ""
    webhook_url = ""
    if medium == "Email":
        recipient_email = st.text_input(
            "Your Email Address 📧",
            placeholder="yourname@gmail.com",
            help="You will receive alerts on this email.",
            key="form_email"
        )
    else:
        webhook_url = st.text_input(
            "Discord Webhook URL 🔗",
            placeholder="https://discord.com/api/webhooks/...",
            help="Enter your Discord channel webhook URL.",
            key="form_webhook"
        )
        
    check_interval = st.number_input(
        "Check Interval (Seconds) ⏱️",
        min_value=10,
        max_value=3600,
        value=30,
        step=5,
        help="Time to wait before refreshing the page. Minimum 10 seconds.",
        key="form_interval"
    )
    
    headless = st.checkbox(
        "Run browser in background (Headless)", 
        value=True,
        help="Uncheck this if you want to visibly see Google Chrome running during monitor checks.",
        key="form_headless"
    )
    
    st.markdown("---")
    
    st.markdown("### ➕ Create New Monitor Task")
    
    # Retrieve scraper class dynamically
    try:
        scraper_cls = ScraperFactory.get_scraper_class(service_provider)
        fields = scraper_cls.get_required_fields()
    except Exception as e:
        st.error(f"Failed to load service provider: {e}")
        st.stop()
        
    with st.form("new_monitor_form", clear_on_submit=False):
        # Dynamically render form fields based on provider metadata
        for field_id, field_meta in fields.items():
            field_type = field_meta.get("type", "text")
            label = field_meta.get("label", field_id.title())
            placeholder = field_meta.get("placeholder", "")
            help_text = field_meta.get("help", "")
            form_key = f"form_{service_provider.lower()}_{field_id}"
            
            if field_type == "text":
                st.text_input(
                    label,
                    placeholder=placeholder,
                    help=help_text,
                    key=form_key
                )
            elif field_type == "date":
                st.date_input(
                    label,
                    min_value=datetime.date.today(),
                    help=help_text,
                    key=form_key
                )
            elif field_type == "text_area":
                st.text_area(
                    label,
                    placeholder=placeholder,
                    help=help_text,
                    key=form_key
                )
        
        submit_btn = st.form_submit_button("Register & Start Daemon 🚀")
        
        if submit_btn:
            # Explicitly load the absolute latest values from the session state keys dynamically
            params_latest = {}
            errors = []
            
            for field_id, field_meta in fields.items():
                form_key = f"form_{service_provider.lower()}_{field_id}"
                val = st.session_state.get(form_key)
                
                # Validation
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(f"Field '{field_meta.get('label')}' is required.")
                
                # Check for BookMyShow URL format
                if field_meta.get("type") == "text" and field_id == "url":
                    if isinstance(val, str) and not val.strip().startswith("http"):
                        errors.append("Enter a valid HTTP/HTTPS URL.")
                
                # Type conversions / formats
                if field_meta.get("type") == "date":
                    params_latest["date_str"] = val.strftime("%Y%m%d")
                elif field_id == "theatres":
                    params_latest["theatres"] = [t.strip() for t in val.split("\n") if t.strip()]
                else:
                    params_latest[field_id] = val if not isinstance(val, str) else val.strip()

            medium_latest = st.session_state.get("form_medium", "Email")
            service_latest = st.session_state.get("form_service", "BookMyShow")
            interval_latest = st.session_state.get("form_interval", 30)
            headless_latest = st.session_state.get("form_headless", True)
            
            email_latest = st.session_state.get("form_email", "").strip()
            webhook_latest = st.session_state.get("form_webhook", "").strip()

            if medium_latest == "Email" and not email_latest:
                errors.append("Enter a recipient email address.")
            if medium_latest == "Discord Webhook" and not webhook_latest:
                errors.append("Enter a Discord Webhook URL.")
                
            if errors:
                for err in errors:
                    st.error(err)
            else:
                notif_config = {}
                if medium_latest == "Email":
                    notif_config = {"recipient_email": email_latest}
                else:
                    notif_config = {"webhook_url": webhook_latest}
                    
                # Instantiate new Monitor Job
                new_job = MonitorJob(
                    params=params_latest,
                    notification_medium=medium_latest,
                    notification_config=notif_config,
                    service_provider=service_latest,
                    check_interval=interval_latest,
                    headless=headless_latest
                )
                
                # Start job background thread
                success = manager.start_job(new_job)
                if success:
                    st.success(f"Successfully registered monitor #{new_job.id}! Daemon thread is now active.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to start monitoring job. An active thread might already be running.")

with col_monitors:
    st.markdown("### 🖥️ Active Monitor Daemons")
    
    active_jobs = manager.get_all_jobs()
    if not active_jobs:
        st.info("No active monitors registered yet. Use the panel on the left to add a new monitoring agent!")
    else:
        # Loop and render card for each active job
        for job in active_jobs:
            render_job_card(job, manager)
            st.markdown("<hr style='border-top: 1px solid rgba(255,255,255,0.05); margin-top: 1.5rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)

# Auto-refresh loop: if toggled and there's a background monitoring thread running
if auto_refresh and any(j.status == "Running" for j in manager.get_all_jobs()):
    time.sleep(10)
    st.rerun()
