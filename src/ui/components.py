# src/ui/components.py

import streamlit as st
from src.core.job import MonitorJob
from src.logger import get_job_logs

def render_job_card(job: MonitorJob, manager) -> None:
    """
    Renders a premium visual card representing a monitor job,
    along with controls to Start, Stop, or Delete it.
    """
    state = job.get_state()
    job_id = state["id"]
    status = state["status"]
    url = state["url"]
    date_str = state["date_str"]
    theatres = state["theatres"]
    medium = state["notification_medium"]
    last_result = state["last_result"]
    last_checked = state["last_checked_at"]
    
    # Format dates/times
    checked_time_str = last_checked.strftime("%Y-%m-%d %H:%M:%S") if last_checked else "Never"
    
    # Map status to custom badge styles
    badge_style_map = {
        "running": "badge badge-running",
        "success": "badge badge-success",
        "error": "badge badge-error",
        "stopped": "badge badge-stopped",
        "idle": "badge badge-idle"
    }
    badge_class = badge_style_map.get(status.lower(), "badge badge-idle")
    
    headless = state.get("headless", True)
    keep_browser_open = state.get("keep_browser_open", True)
    keep_open_str = "Keep Open" if keep_browser_open else "Open/Close"
    run_mode = f"Background ({keep_open_str})" if headless else f"Foreground ({keep_open_str})"
    
    movie_name = state.get("movie_name", "Fetching...")
    
    # HTML representation for custom dashboard styling
    card_html = f"""
    <div class="job-card">
        <div class="card-header">
            <span class="card-title">🎬 <strong>{movie_name}</strong> <span style="font-size:0.85rem; color:#64748b; font-weight:normal;">(ID: #{job_id})</span></span>
            <span class="{badge_class}">{status}</span>
        </div>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Movie Link</div>
                <div class="info-value"><a href="{url}" target="_blank">Link 🔗</a></div>
            </div>
            <div class="info-item">
                <div class="info-label">Date (YYYYMMDD)</div>
                <div class="info-value">📅 {date_str}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Alert Channel</div>
                <div class="info-value">📢 {medium.upper()}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Run Mode</div>
                <div class="info-value">🖥️ {run_mode}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Last Checked</div>
                <div class="info-value">⏱️ {checked_time_str}</div>
            </div>
        </div>
        <div class="info-item" style="margin-top: 0.75rem; width: 100%;">
            <div class="info-label">Target Theatres</div>
            <div class="info-value">🏢 {", ".join(theatres)}</div>
        </div>
        <div class="info-item" style="margin-top: 0.75rem; width: 100%;">
            <div class="info-label">Latest Status</div>
            <div class="info-value" style="font-family: monospace; font-size: 0.85rem;">{last_result}</div>
        </div>
    </div>
    """

    # Grid system: left 5/6 for details and log stream, right 1/6 for control buttons
    col_details, col_controls = st.columns([5, 1])
    
    with col_details:
        st.markdown(card_html, unsafe_allow_html=True)
        # Show real-time console log logs
        with st.expander("📄 Real-time Console Log Stream", expanded=False):
            logs = get_job_logs(job_id, tail_lines=60)
            st.markdown(f'<div class="logs-console">{logs}</div>', unsafe_allow_html=True)
            
    with col_controls:
        # Align buttons vertically inside column
        st.write("") 
        st.write("") 
        
        # Start / Stop Toggle Button
        if status == "Running":
            if st.button("Stop ⏸️", key=f"stop_{job_id}", use_container_width=True):
                manager.stop_job(job_id)
                st.rerun()
        else:
            if st.button("Start ▶️", key=f"start_{job_id}", use_container_width=True):
                # Reset state to Idle before starting
                job.update_state("Idle", "Manual restart requested.")
                manager.start_job(job)
                st.rerun()

        # Delete Button
        if st.button("Delete 🗑️", key=f"del_{job_id}", use_container_width=True):
            manager.delete_job(job_id)
            st.success(f"Deleted job #{job_id}")
            st.rerun()
