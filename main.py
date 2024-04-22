import re

import httpx
import streamlit as st
import time
import zipfile
import os
from io import BytesIO

# Streamlit layout
st.title("API Task Submission and Tracking")

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")


@st.cache_resource
def get_client(api_key) -> httpx.Client:
    client = httpx.Client(
        base_url=API_URL,
        headers={"Authorization": api_key},
        limits=httpx.Limits(max_connections=10),
        timeout=None,
    )
    return client


# User input for API key and task IDs
api_key = st.text_input("Enter API key:")
ids_input = st.text_area("Enter IDs (comma-separated):")
submit_button = st.button("Submit Tasks")
client = get_client(api_key)

if submit_button and api_key and ids_input:
    ids = [id.strip() for id in ids_input.split(",")]
    # Dictionary to track status
    task_status = {id: "Pending" for id in ids}
    st.session_state["task_status"] = task_status

    # Post tasks
    for id in ids:
        response = client.post(f"/ep/{id}/idfmodel")
        if response.status_code == 200:
            task_status[id] = "Submitted"
        else:
            task_status[id] = "Failed to Submit"

    # Polling for task status
    # Polling for task status
    while True:
        all_done = True  # Assume all tasks are done at the start of each cycle
        time.sleep(1)  # Wait before each poll
        for id in ids:
            if task_status[id] not in ["Completed", "Failed"]:
                all_done = False  # If a task is not done, set all_done to False
                status_response = client.get(f"/ep/{id}/idfmodel")
                if status_response.status_code == 200:
                    if "text/plain" in status_response.headers["Content-Type"]:
                        task_status[id] = "Completed"
                else:
                    task_status[id] = "Error Checking Status"
        if all_done:  # If all tasks are done, break the loop
            break

    # Display status updates
    for id, status in task_status.items():
        st.write(f"ID {id}: {status}")

    # Download results if all tasks are completed
    if all([status == "Completed" for status in task_status.values()]):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for id in ids:
                result_response = client.get(f"/ep/{id}/idfmodel")
                if result_response.status_code == 200:
                    # get filename from content-disposition
                    content_disposition = result_response.headers.get(
                        "content-disposition", ""
                    )
                    filename_match = re.search(
                        r'filename="?(?P<filename>[^";]+)"?', content_disposition
                    )
                    filename = filename_match.group("filename")
                    zip_file.writestr(filename, result_response.content)

        st.download_button(
            label="Download Results as ZIP",
            data=zip_buffer.getvalue(),
            file_name="task_results.zip",
            mime="application/zip",
        )
