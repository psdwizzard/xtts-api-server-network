@echo off

echo ===============================================
echo      XTTS Network Connectivity Troubleshoot
echo ===============================================
echo.

REM Get computer's IP addresses
echo 🔍 Your computer's network information:
echo.
ipconfig | findstr /C:"IPv4 Address" /C:"Subnet Mask" /C:"Default Gateway"

echo.
echo 🌐 Your computer can be reached at these addresses:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    for /f "tokens=*" %%b in ("%%a") do (
        echo   http://%%b:8020
    )
)

echo.
echo 🔥 Checking Windows Firewall status...
netsh advfirewall show allprofiles state 2>nul || echo Cannot check firewall status

echo.
echo 📡 Testing if port 8020 is open and listening...
netstat -an | findstr ":8020" && echo ✅ Port 8020 is active || echo ❌ Port 8020 not found - server may not be running

echo.
echo 🛠️  TROUBLESHOOTING STEPS:
echo.
echo 1. FIREWALL ISSUES:
echo    • Windows Defender Firewall may block incoming connections
echo    • When starting the server, click "Allow" if Windows asks
echo    • Or manually allow Python through firewall:
echo      - Control Panel → System and Security → Windows Defender Firewall
echo      - Click "Allow an app through firewall"
echo      - Find Python and check both Private and Public boxes
echo.
echo 2. NETWORK ISSUES:
echo    • Make sure all computers are on the same network
echo    • Try using your computer's actual IP address, not localhost
echo    • Example: http://192.168.1.100:8020 instead of http://localhost:8020
echo.
echo 3. ROUTER/WIFI ISSUES:
echo    • Some routers block device-to-device communication
echo    • Check if "AP Isolation" is disabled in router settings
echo    • Try connecting both computers to the same WiFi network
echo.
echo 4. SERVER BINDING ISSUES:
echo    • Make sure BASE_URL=0.0.0.0:8020 in your batch file
echo    • Server must bind to 0.0.0.0 (all interfaces), not 127.0.0.1 (localhost only)
echo.
echo 5. TEST FROM ANOTHER COMPUTER:
echo    • Open browser on the other computer
echo    • Go to: http://YOUR_ACTUAL_IP:8020/docs
echo    • If this works, the network connection is fine
echo    • If not, it's a firewall/network issue
echo.

echo Press any key to exit...
pause 