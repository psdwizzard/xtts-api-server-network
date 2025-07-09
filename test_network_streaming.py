#!/usr/bin/env python3
"""
XTTS Network Streaming Test Script
This script tests the new network streaming endpoints to verify they work properly.
"""

import requests
import argparse
import sys
import time
from pathlib import Path


def test_server_connection(server_url):
    """Test basic server connectivity"""
    print(f"🔍 Testing server connection to {server_url}")
    try:
        response = requests.get(f"{server_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and accessible")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False


def test_network_streaming_post(server_url, text="Hello, this is a network streaming test", 
                               speaker_wav="female.wav", language="en"):
    """Test the POST endpoint for network streaming"""
    print(f"\n🎵 Testing POST network streaming endpoint...")
    print(f"Text: {text}")
    
    endpoint = f"{server_url}/tts_to_audio_stream/"
    payload = {
        "text": text,
        "speaker_wav": speaker_wav,
        "language": language
    }
    
    try:
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=30)
        
        if response.status_code == 200:
            # Save the audio to a file
            output_file = Path("network_streaming_test_post.wav")
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            duration = time.time() - start_time
            file_size = output_file.stat().st_size
            print(f"✅ POST streaming successful!")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   File size: {file_size:,} bytes")
            print(f"   Saved to: {output_file}")
            return True
        else:
            print(f"❌ POST streaming failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ POST streaming request failed: {e}")
        return False


def test_network_streaming_get(server_url, text="Hello, this is a GET streaming test", 
                              speaker_wav="female.wav", language="en"):
    """Test the GET endpoint for network streaming"""
    print(f"\n🎵 Testing GET network streaming endpoint...")
    print(f"Text: {text}")
    
    params = {
        "text": text,
        "speaker_wav": speaker_wav,
        "language": language
    }
    
    endpoint = f"{server_url}/tts_stream_realtime"
    
    try:
        start_time = time.time()
        response = requests.get(endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            # Save the audio to a file
            output_file = Path("network_streaming_test_get.wav")
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            duration = time.time() - start_time
            file_size = output_file.stat().st_size
            print(f"✅ GET streaming successful!")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   File size: {file_size:,} bytes")
            print(f"   Saved to: {output_file}")
            return True
        else:
            print(f"❌ GET streaming failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ GET streaming request failed: {e}")
        return False


def test_available_speakers(server_url):
    """Test and display available speakers"""
    print(f"\n🎭 Testing available speakers...")
    
    try:
        response = requests.get(f"{server_url}/speakers", timeout=5)
        if response.status_code == 200:
            speakers = response.json()
            print(f"✅ Found {len(speakers)} available speakers:")
            for speaker in speakers[:5]:  # Show first 5
                print(f"   - {speaker}")
            if len(speakers) > 5:
                print(f"   ... and {len(speakers) - 5} more")
            return speakers
        else:
            print(f"❌ Failed to get speakers: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get speakers: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Test XTTS Network Streaming")
    parser.add_argument("--server", default="http://localhost:8020", 
                       help="Server URL (default: http://localhost:8020)")
    parser.add_argument("--text", default="Hello, this is a network streaming test!",
                       help="Text to convert to speech")
    parser.add_argument("--speaker", default="female.wav",
                       help="Speaker voice file")
    parser.add_argument("--language", default="en",
                       help="Language code")
    parser.add_argument("--skip-post", action="store_true",
                       help="Skip POST endpoint test")
    parser.add_argument("--skip-get", action="store_true",
                       help="Skip GET endpoint test")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("       XTTS Network Streaming Test")
    print("=" * 60)
    
    # Test basic connectivity
    if not test_server_connection(args.server):
        print("\n❌ Server connectivity test failed. Make sure:")
        print("   1. XTTS server is running")
        print("   2. STREAM_MODE or STREAM_MODE_IMPROVE is enabled")
        print("   3. Server is accessible at the specified URL")
        print("   4. Firewall allows connections on port 8020")
        sys.exit(1)
    
    # Test available speakers
    speakers = test_available_speakers(args.server)
    if speakers and args.speaker not in speakers:
        print(f"\n⚠️  Warning: Speaker '{args.speaker}' not found in available speakers")
        print(f"   Using it anyway, but you might want to try: {speakers[0] if speakers else 'default'}")
    
    # Run tests
    success_count = 0
    total_tests = 0
    
    if not args.skip_post:
        total_tests += 1
        if test_network_streaming_post(args.server, args.text, args.speaker, args.language):
            success_count += 1
    
    if not args.skip_get:
        total_tests += 1
        if test_network_streaming_get(args.server, args.text, args.speaker, args.language):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("              TEST SUMMARY")
    print("=" * 60)
    
    if success_count == total_tests:
        print(f"🎉 ALL TESTS PASSED! ({success_count}/{total_tests})")
        print("\n✅ Network streaming is working correctly!")
        print("   You can now use these endpoints in your Chrome extension:")
        print(f"   - POST: {args.server}/tts_to_audio_stream/")
        print(f"   - GET:  {args.server}/tts_stream_realtime")
        
        # Check if we created test files
        test_files = []
        if Path("network_streaming_test_post.wav").exists():
            test_files.append("network_streaming_test_post.wav")
        if Path("network_streaming_test_get.wav").exists():
            test_files.append("network_streaming_test_get.wav")
        
        if test_files:
            print(f"\n🔊 Test audio files created: {', '.join(test_files)}")
            print("   You can play these files to verify audio quality")
            
    else:
        print(f"❌ SOME TESTS FAILED ({success_count}/{total_tests})")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check server logs for error messages")
        print("   2. Verify STREAM_MODE_IMPROVE=true is set")
        print("   3. Ensure the server has the required models loaded")
        print("   4. Try with a different speaker voice")
        print("   5. Check network connectivity between client and server")
        
        sys.exit(1)


if __name__ == "__main__":
    main() 