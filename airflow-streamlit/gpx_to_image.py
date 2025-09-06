#!/usr/bin/env python3
"""
Streamlit app for GPX to Image conversion using local Airflow API
"""

import streamlit as st
import requests
import base64
import json
import ast
import time
import io
import gzip
from typing import Dict, List, Optional

# Airflow configuration
AIRFLOW_BASE_URL = "http://localhost:8080"
AIRFLOW_USERNAME = "evgenyarbatov"
AIRFLOW_PASSWORD = "djAxWzNCvdDq"
DAG_ID = "gpx_to_image_dag"

class GPXProcessor:
    def __init__(self):
        self.auth = (AIRFLOW_USERNAME, AIRFLOW_PASSWORD)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def submit_gpx(self, gpx_content: str) -> Optional[str]:
        """Submit GPX data to Airflow DAG and return dag_run_id"""
        try:
            # Check file size and compress if needed
            original_size = len(gpx_content.encode())
            
            if original_size > 1024 * 1024:  # 1MB threshold
                # Compress large files
                compressed = gzip.compress(gpx_content.encode())
                gpx_base64 = base64.b64encode(compressed).decode()
                is_compressed = True
                # Silently compress large files
                pass
            else:
                # Regular encoding for smaller files
                gpx_base64 = base64.b64encode(gpx_content.encode()).decode()
                is_compressed = False
            
            # Prepare payload
            payload = {
                "conf": {
                    "gpx_data_base64": gpx_base64,
                    "is_compressed": is_compressed
                }
            }
            
            # Submit to DAG
            url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns"
            response = self.session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("dag_run_id")
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 413:
                # Silently skip files that are too large
                return None
            else:
                st.error(f"HTTP error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"Failed to submit GPX: {str(e)}")
            return None
    
    def check_dag_status(self, dag_run_id: str) -> Dict:
        """Check the status of a DAG run"""
        try:
            url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            result = response.json()
            return {
                "dag_run_id": result.get("dag_run_id"),
                "state": result.get("state"),
                "start_date": result.get("start_date"),
                "end_date": result.get("end_date")
            }
            
        except Exception as e:
            st.error(f"Failed to check DAG status: {str(e)}")
            return {"state": "error"}
    
    def get_generated_image(self, dag_run_id: str) -> Optional[bytes]:
        """Retrieve the generated image from DAG run"""
        try:
            url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{DAG_ID}/dagRuns/{dag_run_id}/taskInstances/process_gpx_data/xcomEntries/return_value"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            value_str = data['value']
            
            # Parse the string representation of the dictionary
            result_dict = ast.literal_eval(value_str)
            
            # Extract and decode the base64 image
            image_base64 = result_dict['image_base64']
            image_bytes = base64.b64decode(image_base64)
            
            return image_bytes
            
        except Exception as e:
            # Silently return None if image retrieval fails
            return None

def main():
    st.set_page_config(
        page_title="GPX to Image Converter",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🗺️ GPX to Image Converter")
    
    # Initialize session state
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    if 'processor' not in st.session_state:
        st.session_state.processor = GPXProcessor()
    
    # File upload section
    uploaded_files = st.file_uploader(
        "Choose GPX files",
        type=['gpx'],
        accept_multiple_files=True,
        help="Select one or more GPX files to convert to images"
    )
    
    if uploaded_files:
        # Process button
        if st.button("Plot", type="primary", use_container_width=True):
            process_files(uploaded_files)
    
    # Display results
    if st.session_state.processed_files:
        display_results()

def process_files(uploaded_files):
    """Process uploaded GPX files"""
    processor = st.session_state.processor
    
    # Clear previous results
    st.session_state.processed_files = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Read GPX content
        gpx_content = uploaded_file.read().decode('utf-8')
        
        # Submit to Airflow
        dag_run_id = processor.submit_gpx(gpx_content)
        
        if dag_run_id:
            file_info = {
                "filename": uploaded_file.name,
                "dag_run_id": dag_run_id,
                "status": "submitted",
                "image_data": None
            }
            st.session_state.processed_files.append(file_info)
        
        # Update progress
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.empty()
    progress_bar.empty()

def display_results():
    """Display processing results and images in a grid"""
    processor = st.session_state.processor
    
    # Check for pending jobs
    has_pending = any(
        file_info["status"] in ["submitted", "running", "queued"] 
        for file_info in st.session_state.processed_files
    )
    
    # Always update status and get images for all files
    for file_info in st.session_state.processed_files:
        if file_info["status"] not in ["success", "failed"] and file_info.get("dag_run_id"):
            status_info = processor.check_dag_status(file_info["dag_run_id"])
            file_info["status"] = status_info["state"]
            
        if file_info["status"] == "success" and not file_info.get("image_data"):
            image_bytes = processor.get_generated_image(file_info["dag_run_id"])
            if image_bytes:
                file_info["image_data"] = image_bytes
    
    if has_pending:
        # Show processing indicator and auto-refresh
        st.info("⏳ Processing files...")
        st.rerun()
    
    # Display images in grid
    files_with_images = [f for f in st.session_state.processed_files if f.get("image_data")]
    
    if files_with_images:
        for i in range(0, len(files_with_images), 5):
            cols = st.columns(5)
            for j, file_info in enumerate(files_with_images[i:i+5]):
                with cols[j]:
                    st.image(
                        file_info["image_data"],
                        use_column_width=True
                    )

if __name__ == "__main__":
    main()