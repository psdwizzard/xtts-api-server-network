@echo off

echo =====================================================
echo      XTTS API Server - Network Streaming Enabled
echo =====================================================
echo.

echo Activating virtual environment...
call venv\Scripts\activate

REM Enable network streaming mode - settings now passed as command line arguments
set STREAM_PLAY_SYNC=false

echo Starting XTTS API Server with Network Streaming...
echo.
echo 🎵 Network streaming ENABLED! Audio will stream to client devices.
echo 📡 Server will be accessible on ALL network interfaces (0.0.0.0:8020)
echo.
echo To find your computer's IP address for external access:
echo   1. Open another command prompt
echo   2. Run: ipconfig
echo   3. Look for "IPv4 Address" under your active network adapter
echo   4. Use that IP instead of "localhost" from other devices
echo.
echo Network streaming endpoints:
echo   POST: http://YOUR_IP_ADDRESS:8020/tts_to_audio_stream/
echo   GET:  http://YOUR_IP_ADDRESS:8020/tts_stream_realtime
echo   Docs: http://YOUR_IP_ADDRESS:8020/docs
echo.
echo Starting server...

python -m xtts_api_server --listen --streaming-mode-improve --deepspeed --lowvram --use-cache

echo.
echo Server stopped. Press any key to exit.
pause
