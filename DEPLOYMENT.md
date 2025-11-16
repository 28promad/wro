# Raspberry Pi Deployment Guide

## Step 1: Prepare Your Raspberry Pi

### SSH into your Pi
```bash
ssh pi@<pi-ip>
```

### Update system
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python dependencies (if not already installed)
```bash
sudo apt install python3-pip python3-dev -y
```

## Step 2: Clone/Copy Project Files

### Option A: Clone from GitHub (if you have git)
```bash
cd ~/
git clone <your-repo-url> rover
cd rover
```

### Option B: Copy files manually
```bash
# On your computer, copy the entire project directory to Pi
scp -r ~/Documents/Hackathon\ Stuff/wro pi@<pi-ip>:~/rover
```

## Step 3: Create Project Directory Structure

```bash
cd ~/rover
# Verify all files are in place
ls -la

# Should see:
# main_pi.py
# web_app.py
# web_app_simple.py
# rover_data_service.py
# motor_control.py
# requirements.txt
# templates/dashboard.html
# templates/dashboard_simple.html
# comms/
# rover_logs/
```

## Step 4: Install Python Packages

```bash
cd ~/rover

# Option A: For full WebSocket support (recommended)
pip install -r requirements.txt

# Option B: If you only have Flask
pip install flask==2.3.3
pip install flask-socketio==5.3.4 python-socketio==5.9.0 python-engineio==4.7.1

# Option C: If WebSocket fails, just Flask
pip install flask==2.3.3
```

## Step 5: Test the Setup

### Terminal 1: Run main rover controller
```bash
cd ~/rover
python3 main_pi.py
```

Output should look like:
```
Rover initializing (BLE)...
Waiting for Raspberry Pi...
```

### Terminal 2: Run web dashboard
```bash
cd ~/rover
python3 web_app.py
```

Output should look like:
```
Starting Databot Rover Dashboard...
Access at: http://<pi-ip>:5000
 * Running on http://0.0.0.0:5000
```

### Terminal 3: Test dashboard access
```bash
# From your computer or another Pi
curl http://<pi-ip>:5000
```

You should get HTML response.

### Access from Browser
- Open: `http://<pi-ip>:5000`
- You should see the dashboard (may show "Disconnected" if databot not connected)

## Step 6: Set Up Auto-Start (Optional)

### Create systemd service file

```bash
sudo nano /etc/systemd/system/rover-main.service
```

Paste this:
```ini
[Unit]
Description=Databot Rover Main Controller
After=network.target
Wants=rover-dashboard.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rover
ExecStart=/usr/bin/python3 /home/pi/rover/main_pi.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save with `Ctrl+X`, `Y`, `Enter`

### Create dashboard service

```bash
sudo nano /etc/systemd/system/rover-dashboard.service
```

Paste this:
```ini
[Unit]
Description=Databot Rover Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rover
ExecStart=/usr/bin/python3 /home/pi/rover/web_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save with `Ctrl+X`, `Y`, `Enter`

### Enable services

```bash
sudo systemctl daemon-reload
sudo systemctl enable rover-main.service
sudo systemctl enable rover-dashboard.service
```

### Start services

```bash
sudo systemctl start rover-main.service
sudo systemctl start rover-dashboard.service
```

### Check status

```bash
sudo systemctl status rover-main.service
sudo systemctl status rover-dashboard.service
```

Both should show `active (running)`

### View logs

```bash
sudo journalctl -u rover-main.service -f
sudo journalctl -u rover-dashboard.service -f
```

## Step 7: Access from Network

### Find your Pi's IP
```bash
hostname -I
```

### From any device on network
Open browser: `http://<pi-ip>:5000`

### From outside network (advanced)
1. Configure port forwarding on router
2. Consider using VPN or reverse proxy
3. Add authentication to Flask app

## Step 8: Troubleshooting

### Port 5000 already in use
```bash
# Find process using port
sudo lsof -i :5000

# Kill it if needed
sudo kill -9 <PID>

# Or change port in web_app.py (line ~132):
socketio.run(app, host='0.0.0.0', port=5001, ...)
```

### Module not found errors
```bash
# Install missing package
pip install <package-name>

# Or reinstall all requirements
pip install -r requirements.txt --force-reinstall
```

### Dashboard shows "Cannot connect"
1. Check if `main_pi.py` is running: `ps aux | grep main_pi.py`
2. Check if `web_app.py` is running: `ps aux | grep web_app.py`
3. Check firewall: `sudo ufw allow 5000`
4. Check port: `netstat -an | grep 5000`

### Databot not connecting
1. Check BLE hardware: `hcitool scan`
2. Check `comms/central.py` configuration
3. Look for error messages in `main_pi.py` terminal

### High CPU usage
1. Reduce update frequency (increase sleep time in main_pi.py)
2. Reduce chart history limit (in rover_data_service.py)
3. Check for infinite loops in motor_control.py

### CSV file growing too fast
1. Implement file rotation (daily archives)
2. Or disable CSV logging entirely:
   ```python
   # Comment out these lines in main_pi.py
   # with open(CSV_FILE, 'a', newline='') as f:
   #     ...
   ```

## Step 9: Production Checklist

### Security
- [ ] Change Flask debug mode: `debug=False` in web_app.py
- [ ] Add authentication if exposed to internet
- [ ] Use HTTPS with SSL certificate
- [ ] Restrict firewall access

### Performance
- [ ] Monitor memory usage: `free -h`
- [ ] Monitor disk space: `df -h`
- [ ] Monitor CPU: `top` or `htop`

### Maintenance
- [ ] Set up log rotation for CSV files
- [ ] Monitor service uptime
- [ ] Plan backup strategy
- [ ] Document any custom configurations

### Monitoring
```bash
# Watch main_pi.py
watch -n 1 'ps aux | grep main_pi'

# Watch memory
watch -n 1 'free -h'

# Watch disk
watch -n 1 'df -h'

# Watch logs
journalctl -u rover-main.service -n 50 -f
```

## Step 10: Useful Commands

### Stop services
```bash
sudo systemctl stop rover-main.service
sudo systemctl stop rover-dashboard.service
```

### Restart services
```bash
sudo systemctl restart rover-main.service
sudo systemctl restart rover-dashboard.service
```

### View combined logs
```bash
sudo journalctl -u rover-main.service -u rover-dashboard.service -f
```

### SSH directly to main loop
```bash
ssh pi@<pi-ip> "cd ~/rover && python3 main_pi.py"
```

### Remote port forwarding (from your computer)
```bash
ssh -L 5000:localhost:5000 pi@<pi-ip>
# Now access http://localhost:5000 from your computer
```

## Performance Tips

### For Better Real-Time Performance
1. Use **web_app.py** (WebSocket) instead of web_app_simple.py
2. Reduce chart history: `RoverDataService(max_history=150)`
3. Increase motor loop sleep: `await asyncio.sleep(0.1)` (50Hz → 10Hz)

### For Lower Memory Usage
1. Reduce in-memory buffer size
2. Disable CSV logging during long missions
3. Archive old CSV files

### For Better Stability
1. Use systemd services (auto-restart)
2. Monitor disk space
3. Implement watchdog timer
4. Set up error notifications

## Network Optimization

### Local Network Only
```python
# web_app.py line ~132
socketio.run(app, host='127.0.0.1', port=5000)
# Now only accessible from Pi itself
```

### LAN Only (Recommended for Security)
```python
# web_app.py line ~132
socketio.run(app, host='192.168.1.100', port=5000)
# Only accessible on local network
```

### Accessible Everywhere (Use with caution!)
```python
# web_app.py line ~132
socketio.run(app, host='0.0.0.0', port=5000)
# Accessible from anywhere (firewall dependent)
```

## Debugging Commands

### Check service health
```bash
systemctl status rover-main.service
systemctl status rover-dashboard.service
```

### Restart on failure
```bash
sudo systemctl restart rover-main.service
sudo systemctl restart rover-dashboard.service
```

### Check resource usage
```bash
ps aux | grep python3
free -h
df -h
```

### Test connectivity
```bash
# From another device
curl http://<pi-ip>:5000
```

---

**You're ready to deploy!** 🚀

Once running, access the dashboard at:
```
http://<your-pi-ip>:5000
```
