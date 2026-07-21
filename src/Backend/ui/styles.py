# src/ui/styles.py

import streamlit as st

def inject_premium_styles():
    """Injects custom CSS styles to give the Streamlit app a modern, premium look."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Main Layout Customizations */
    .stApp {
        font-family: 'Outfit', sans-serif;
        background-color: #0d0f14;
        color: #e2e8f0;
    }
    
    /* Header Gradient Style */
    .gradient-text {
        background: linear-gradient(135deg, #f43f5e, #ec4899, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle-text {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 2rem;
    }

    /* Premium Dark Mode Cards */
    .job-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .job-card:hover {
        transform: translateY(-2px);
        border-color: rgba(236, 72, 153, 0.4);
    }
    
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 0.75rem;
    }
    
    .card-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #ffffff;
    }

    /* Custom Status Badges */
    .badge {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        letter-spacing: 0.05em;
        display: inline-block;
    }
    .badge-running {
        background-color: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
        animation: pulse 2s infinite;
    }
    .badge-success {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.2);
    }
    .badge-error {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-stopped {
        background-color: rgba(107, 114, 128, 0.15);
        color: #9ca3af;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }
    .badge-idle {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Details Container styling */
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
    .info-item {
        background: rgba(15, 23, 42, 0.3);
        padding: 0.5rem 0.75rem;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.03);
    }
    .info-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
        font-weight: 600;
    }
    .info-value {
        color: #cbd5e1;
        font-weight: 500;
    }
    .info-value a {
        color: #ec4899;
        text-decoration: none;
    }
    .info-value a:hover {
        text-decoration: underline;
    }

    /* Logs Console window styling */
    .logs-console {
        background-color: #07090e;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.8rem;
        color: #a7f3d0;
        max-height: 200px;
        overflow-y: auto;
        white-space: pre-wrap;
        margin-top: 1rem;
        border-left: 3px solid #ec4899;
    }

    /* Breathing pulse animation */
    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.6;
        }
    }
    
    /* Input Fields Styling */
    div[data-baseweb="input"] {
        background-color: #1e293b !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: white !important;
    }
    
    /* Submit Buttons Styling */
    .stButton>button {
        background: linear-gradient(135deg, #ec4899, #ef4444) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(236, 72, 153, 0.3) !important;
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.45) !important;
    }
    
    /* Hide Streamlit input helper instructions (like "Press Ctrl+Enter to apply") */
    div[data-testid="InputInstructions"], 
    .stTextArea small {
        display: none !important;
    }
    
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
