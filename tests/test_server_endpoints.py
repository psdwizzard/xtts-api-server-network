import pytest
import requests
import time
import subprocess
import os
import sys

BASE_URL = "http://127.0.0.1:8020"
# Use a default speaker that is likely to exist
SPEAKER_NAME = "M_Cary" 

@pytest.fixture(scope="session", autouse=True)
def start_server():
    """Starts the XTTS API server as a background process for the test session."""
    server_process = None
    try:
        python_executable = sys.executable
        
        # Enable streaming mode for tests
        env = os.environ.copy()
        env["STREAM_MODE"] = "true"
        env["STREAM_MODE_IMPROVE"] = "true"
        
        command = [python_executable, "-m", "xtts_api_server"]
        
        server_process = subprocess.Popen(command, env=env, cwd=os.getcwd(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        retries = 30
        for i in range(retries):
            try:
                response = requests.get(f"{BASE_URL}/speakers", timeout=10)
                if response.status_code == 200:
                    print("Server is ready.")
                    break
            except requests.ConnectionError:
                time.sleep(2)
        else:
            stdout, stderr = server_process.communicate()
            print("Server stdout:\n", stdout)
            print("Server stderr:\n", stderr)
            pytest.fail("Server did not start within the expected time.")
            
        yield
        
    finally:
        if server_process:
            print("Shutting down server...")
            stdout, stderr = server_process.communicate()
            print("Server stdout:\n", stdout)
            print("Server stderr:\n", stderr)
            server_process.terminate()
            server_process.wait(timeout=10)

def test_get_speakers():
    """Tests the /speakers endpoint."""
    response = requests.get(f"{BASE_URL}/speakers")
    assert response.status_code == 200
    json_response = response.json()
    assert isinstance(json_response, list)
    # Check if the speaker we intend to use exists in the list of dictionaries
    speaker_found = any(speaker['name'] == SPEAKER_NAME for speaker in json_response)
    assert speaker_found, f"Test speaker '{SPEAKER_NAME}' not found on server."

def test_tts_to_audio_non_streaming():
    """Tests the standard non-streaming TTS endpoint."""
    payload = {
        "text": "Hello, this is a test.",
        "speaker_wav": SPEAKER_NAME, # Use speaker name here
        "language": "en"
    }
    response = requests.post(f"{BASE_URL}/tts_to_audio/", json=payload)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'audio/wav'
    assert len(response.content) > 1000 

def test_tts_to_audio_stream():
    """Tests the network streaming TTS endpoint."""
    payload = {
        "text": "This is a streaming test to see if it works correctly.",
        "speaker_wav": SPEAKER_NAME, # Use speaker name here
        "language": "en"
    }
    
    with requests.post(f"{BASE_URL}/tts_to_audio_stream/", json=payload, stream=True) as response:
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'audio/wav'
        
        chunk_received = False
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                chunk_received = True
                assert isinstance(chunk, bytes)
                assert len(chunk) > 0
                break 
        
        assert chunk_received, "Did not receive any streaming data."

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 