# 🔋 macOS Battery Forensics & Automation

A professional-grade forensic battery monitoring tool for macOS that extracts kernel-level metrics (via `ioreg`) and logs detailed health reports to a Notion database.

## 🚀 Features

- **Forensic Extraction**: Bypasses the standard UI to access raw kernel battery data (XML plist parsing).
- **Notion Integration**: Automatically pushes rich engineering reports to your Notion workspace.
- **Auto-Schema Configuration**: Automatically creates the necessary database columns on the first run.
- **Automated Monitoring**: Includes `launchd` configuration for reliable daily execution (even after sleep).

## 📊 Metrics Captured

- **Real Health %**: True battery capacity vs. design capacity (more accurate than System Settings).
- **Cycle Count**: Total charge cycles.
- **Power Flow**: Real-time Voltage (V), Amperage (mA), and Wattage (W).
- **Thermals**: Precise battery temperature.
- **Capacity Analysis**: Design Capacity vs. Current Max Capacity (mAh).

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/UthitSawatdee/BatteryMonitor.git
cd BatteryMonitor
```

### 2. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Configure Notion
1. Create a [Notion Integration](https://www.notion.so/my-integrations).
2. Create a new Database in Notion.
3. Share the database with your integration.
4. Get your `NOTION_API_KEY` and `NOTION_DATABASE_ID`.

## 🤖 Automation Setup (launchd)

We use `launchd` (native macOS scheduler) for robust reliability.

1. **Install the script**:
   ```bash
   mkdir -p ~/.local/bin
   cp mac_battery_forensics.py ~/.local/bin/
   chmod +x ~/.local/bin/mac_battery_forensics.py
   ```

2. **Edit the plist configuration**:
   Edit `com.template.batterymonitor.plist` to include your API keys and username, then save as `com.yourname.batterymonitor.plist`.

3. **Load the job**:
   ```bash
   cp com.yourname.batterymonitor.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.yourname.batterymonitor.plist
   ```

## 📄 License
MIT License
