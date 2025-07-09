# XTTS Network Audio Streaming Setup Guide

This guide explains how to set up your XTTS API server to stream audio over the network to other computers in your house, solving the limitation where audio only plays on the server machine.

## 🎯 Problem Solved
- **Before**: Audio streaming only worked on the local server machine
- **After**: Audio streams over the network to any client (Chrome extension, web browser, etc.)

## 🔧 Configuration

### 1. Environment Variables

Set these environment variables to enable network streaming:

```bash
# Required: Enable streaming mode
STREAM_MODE=true
# OR use improved streaming (recommended)
STREAM_MODE_IMPROVE=true

# Optional: Streaming behavior
STREAM_PLAY_SYNC=false  # Use async for better performance

# Server configuration
BASE_URL=0.0.0.0:8020  # Listen on all interfaces
DEVICE=cuda            # Or cpu if no GPU
```

### 2. Windows Batch File Example

Update your `run_Server.bat`:

```batch
@echo off
set STREAM_MODE_IMPROVE=true
set STREAM_PLAY_SYNC=false
set BASE_URL=0.0.0.0:8020
set DEVICE=cuda

python -m xtts_api_server
pause
```

### 3. Linux/Mac Shell Script Example

Create a `run_server.sh`:

```bash
#!/bin/bash
export STREAM_MODE_IMPROVE=true
export STREAM_PLAY_SYNC=false
export BASE_URL=0.0.0.0:8020
export DEVICE=cuda

python -m xtts_api_server
```

## 🚀 New API Endpoints

### 1. Real-time Streaming (POST) - Recommended for Chrome Extensions

```javascript
// POST endpoint with JSON body
fetch('http://YOUR_SERVER_IP:8020/tts_to_audio_stream/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        text: "Hello, this is network streaming!",
        speaker_wav: "female.wav",
        language: "en"
    })
})
.then(response => response.blob())
.then(blob => {
    const audio = new Audio(URL.createObjectURL(blob));
    audio.play();
});
```

### 2. Real-time Streaming (GET) - Simple URL-based

```javascript
// GET endpoint with query parameters
const params = new URLSearchParams({
    text: "Hello, this is network streaming!",
    speaker_wav: "female.wav",
    language: "en"
});

const audio = new Audio(`http://YOUR_SERVER_IP:8020/tts_stream_realtime?${params}`);
audio.play();
```

## 🌐 Network Configuration

### 1. Server IP Address

Find your server's IP address:

**Windows:**
```cmd
ipconfig
```

**Linux/Mac:**
```bash
ip addr show
# or
ifconfig
```

### 2. Firewall Configuration

Make sure port 8020 is open on your server:

**Windows Firewall:**
```cmd
netsh advfirewall firewall add rule name="XTTS Server" dir=in action=allow protocol=TCP localport=8020
```

**Linux (ufw):**
```bash
sudo ufw allow 8020
```

### 3. Test Network Access

From another computer, test if the server is accessible:
```bash
curl http://YOUR_SERVER_IP:8020/docs
```

## 🎭 Chrome Extension Integration

### Update your Chrome extension to use network streaming:

1. **Replace the server URL** in your extension:
   ```javascript
   const serverUrl = 'http://YOUR_SERVER_IP:8020';  // Replace YOUR_SERVER_IP
   ```

2. **Use the network streaming endpoint**:
   ```javascript
   // Instead of /tts_to_audio/ use /tts_to_audio_stream/
   const response = await fetch(`${serverUrl}/tts_to_audio_stream/`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
           text: selectedText,
           speaker_wav: 'female.wav',
           language: 'en'
       })
   });
   ```

3. **Handle the streaming response**:
   ```javascript
   const audioBlob = await response.blob();
   const audioUrl = URL.createObjectURL(audioBlob);
   const audio = new Audio(audioUrl);
   await audio.play();
   ```

## 🔍 Testing

### 1. Test Local Streaming

```bash
curl -X POST "http://localhost:8020/tts_to_audio_stream/" \
     -H "Content-Type: application/json" \
     -d '{"text":"Test", "speaker_wav":"female.wav", "language":"en"}' \
     --output test_audio.wav
```

### 2. Test Network Streaming

From another computer:
```bash
curl -X POST "http://YOUR_SERVER_IP:8020/tts_to_audio_stream/" \
     -H "Content-Type: application/json" \
     -d '{"text":"Network test", "speaker_wav":"female.wav", "language":"en"}' \
     --output network_test.wav
```

### 3. Browser Console Test

Open browser console on any computer and run:
```javascript
fetch('http://YOUR_SERVER_IP:8020/tts_stream_realtime?text=Hello&speaker_wav=female.wav&language=en')
    .then(response => response.blob())
    .then(blob => {
        const audio = new Audio(URL.createObjectURL(blob));
        audio.play();
    });
```

## 🚨 Troubleshooting

### Common Issues:

1. **"Connection refused"**
   - Check if server is running
   - Verify firewall settings
   - Ensure server binds to 0.0.0.0, not 127.0.0.1

2. **"CORS errors"**
   - The server has CORS enabled for all origins
   - Check browser console for specific errors

3. **"Streaming mode not enabled"**
   - Set `STREAM_MODE=true` or `STREAM_MODE_IMPROVE=true`
   - Restart the server after changing environment variables

4. **Audio doesn't play on remote machine**
   - Verify you're using the new endpoints (`/tts_to_audio_stream/` or `/tts_stream_realtime`)
   - Check network connectivity
   - Test with curl first

### Debug Mode:

Enable debug logging in your Chrome extension:
```javascript
const streamer = new XTTSNetworkStreamer('http://YOUR_SERVER_IP:8020');
streamer.debug = true;  // Enable debug logging
```

## 📋 Summary

✅ **What's Fixed:**
- Audio now streams over network instead of playing only on server
- Real-time streaming with minimal latency
- Compatible with Chrome extensions and web browsers
- Works across different computers in your network

✅ **New Features:**
- `/tts_to_audio_stream/` - POST endpoint for structured requests
- `/tts_stream_realtime` - GET endpoint for simple URL-based requests
- Proper audio chunking and streaming
- Network-friendly audio format handling

✅ **Maintained:**
- All existing functionality still works
- Backward compatibility with existing endpoints
- Same audio quality and voice options

## 🔥 **URGENT FIX: Your Specific Issues**

### ❌ **Issue 1: "Real-time streaming requires STREAM_MODE or STREAM_MODE_IMPROVE to be enabled"**

**Quick Fix:**
1. **Stop your server** (Ctrl+C if running)
2. **Use the updated batch file**: `run_Server.bat`
3. **Or set manually**:
   ```cmd
   set STREAM_MODE_IMPROVE=true
   python -m xtts_api_server
   ```

**Why this happens:** Environment variable not set before Python starts

### ❌ **Issue 2: "Cannot connect from other computers"**

**Quick Fix:**
1. **Allow Python through Windows Firewall**:
   - When server starts, Windows asks about firewall → Click **"Allow"**
   - Server must show: `Starting XTTS API Server on 0.0.0.0:8020`

2. **Find your IP address**:
   ```cmd
   ipconfig
   ```
   Look for IPv4 Address (like 192.168.1.100)

3. **Test from other computer**:
   - Use: `http://192.168.1.100:8020/docs` ✅
   - NOT: `http://localhost:8020/docs` ❌

4. **Run network diagnostics**:
   ```cmd
   network_troubleshoot.bat
   ```

### 🛠️ **Step-by-Step Debugging**

1. **Start fresh**:
   ```cmd
   # Stop any running server
   # Open new command prompt
   set STREAM_MODE_IMPROVE=true
   python -m xtts_api_server
   ```

2. **Check server logs** - should see:
   ```
   ✅ STREAM_MODE_IMPROVE is correctly set
   🎵 Network streaming enabled!
   Starting XTTS API Server on 0.0.0.0:8020
   ```

3. **Test locally first**:
   - Open: `http://localhost:8020/debug/config`
   - Look for: `"streaming_status": "✅ ENABLED"`

4. **Test from other computer**:
   - Use your actual IP: `http://YOUR_IP:8020/debug/config`
   - If this fails, it's a firewall/network issue

### 🚨 **Emergency Quick Fix**

If everything fails, run this exact sequence:

```cmd
# 1. Stop server (Ctrl+C)
# 2. Close command prompt
# 3. Open NEW command prompt as Administrator
# 4. Navigate to your project folder
# 5. Run:

set STREAM_MODE_IMPROVE=true
set BASE_URL=0.0.0.0:8020
call venv\Scripts\activate
python -m xtts_api_server

# 6. When Windows asks about firewall → Click "Allow"
# 7. Test from server: http://localhost:8020/debug/config
# 8. Find your IP with: ipconfig
# 9. Test from other PC: http://YOUR_IP:8020/debug/config
```

**If this still doesn't work**: The issue is network/router configuration blocking device-to-device communication. 