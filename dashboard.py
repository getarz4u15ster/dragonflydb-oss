"""
Streamlit dashboard: top noisy services, stream/worker health, active incidents.
Auto-refreshes every 2 seconds.
"""
import time
import requests
import streamlit as st

API = "http://localhost:8080"

st.set_page_config(page_title="Redis / Dragonfly OSS DevOps OpsView", layout="wide")
st.title("Redis / Dragonfly OSS DevOps OpsView")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Noisy Services (live)")
    try:
        top = requests.get(f"{API}/top", timeout=3).json()
        st.table(top)
    except Exception as e:
        st.error(f"Could not reach API: {e}")

with col2:
    st.subheader("Stream / Worker Health")
    try:
        stats = requests.get(f"{API}/stats", timeout=3).json()
        st.json(stats)
    except Exception as e:
        st.error(f"Could not reach API: {e}")

st.subheader("Active Incidents (auto-expire if quiet)")
try:
    incidents = requests.get(f"{API}/incidents", timeout=3).json()
    st.table(
        [
            {
                "incident_id": i.get("incident_id"),
                "service": i.get("service"),
                "event_type": i.get("event_type"),
                "max_severity": i.get("max_severity"),
                "status": i.get("status"),
                "last_seen": i.get("last_seen"),
                "message": i.get("message"),
            }
            for i in incidents
        ]
    )
except Exception as e:
    st.error(f"Could not reach API: {e}")

st.caption("Auto-refreshing every 2 seconds")
time.sleep(2)
st.rerun()
