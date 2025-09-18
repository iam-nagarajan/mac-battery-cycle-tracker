# 🔋 Mac Battery Cycle Tracker

A comprehensive macOS application that tracks your MacBook's battery cycle count over time and provides beautiful web-based visualizations of battery health trends.

![Battery Tracker Dashboard](https://img.shields.io/badge/Platform-macOS-blue) ![Python](https://img.shields.io/badge/Python-3.7+-green) ![Flask](https://img.shields.io/badge/Flask-2.3+-red)

## Features

- **Real-time Battery Monitoring**: Automatically extracts battery cycle count and health information from macOS system
- **Historical Data Storage**: Stores battery data in SQLite database with timestamps
- **Beautiful Web Dashboard**: Modern, responsive web interface with interactive charts
- **Trend Analysis**: Visualize battery health degradation over time
- **Automated Collection**: Schedule automatic data collection with cron jobs
- **REST API**: Full API for integration with other tools
- **Multiple Data Sources**: Uses both `system_profiler` and `ioreg` for reliable data extraction

## Screenshots

The dashboard provides:
- Current battery cycle count and health percentage
- Battery condition status
- Interactive charts showing trends over time
- Configurable time ranges (7 days to 1 year)
- Real-time data updates

## Quick Start

### Prerequisites

- macOS (tested on macOS 10.14+)
- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. **Clone or download this repository**:
   ```bash
   cd mac-battery-cycle
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

3. **Start the web server**:
   ```bash
   source venv/bin/activate
   python3 app.py
   ```

4. **Open your browser** and navigate to `http://localhost:5000`

## Manual Installation

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test battery tracker
python3 battery_tracker.py --status

# Start web server
python3 app.py
```

## Usage

### Command Line Interface

The `battery_tracker.py` script can be used standalone:

```bash
# Show current battery status
python3 battery_tracker.py --status

# Record current battery cycle to database
python3 battery_tracker.py --record

# Show battery history (default: 30 days)
python3 battery_tracker.py --history 90

# Use custom database file
python3 battery_tracker.py --db my_battery.db --record
```

### Web Dashboard

1. Start the Flask server: `python3 app.py`
2. Open `http://localhost:5000` in your browser
3. View real-time battery stats and historical trends
4. Use the "Record Now" button to manually record data
5. Select different time ranges to analyze trends

### API Endpoints

The application provides a REST API:

- `GET /api/current` - Get current battery information
- `GET /api/history?days=30` - Get battery history
- `POST /api/record` - Record current battery cycle
- `GET /api/stats` - Get battery statistics

Example API usage:
```bash
# Get current battery info
curl http://localhost:5000/api/current

# Get 90 days of history
curl http://localhost:5000/api/history?days=90

# Record current cycle
curl -X POST http://localhost:5000/api/record
```

## Automated Data Collection

Set up automatic battery monitoring using cron:

1. **Edit your crontab**:
   ```bash
   crontab -e
   ```

2. **Add one of these lines**:
   ```bash
   # Record every 6 hours
   0 */6 * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh
   
   # Record every hour
   0 * * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh

   # Record daily at 9 AM
   0 9 * * * /path-to/folder/mac-battery-cycle/cron_battery_check.sh
   ```

3. **Check cron logs**:
   ```bash
   tail -f battery_tracker.log
   ```

## Database Schema

The SQLite database stores battery information in the `battery_cycles` table:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | DATETIME | When the record was created |
| cycle_count | INTEGER | Battery cycle count |
| max_capacity | INTEGER | Current maximum capacity (mAh) |
| design_capacity | INTEGER | Original design capacity (mAh) |
| health_percentage | REAL | Battery health percentage |
| battery_condition | TEXT | Battery condition (Normal, Replace Soon, etc.) |
| charge_remaining | REAL | Current charge remaining (mAh) |

## File Structure

```
mac-battery-cycle/
├── battery_tracker.py      # Core battery tracking module
├── app.py                  # Flask web server
├── templates/
│   └── dashboard.html      # Web dashboard interface
├── requirements.txt        # Python dependencies
├── setup.sh               # Automated setup script
├── cron_battery_check.sh  # Cron job script
├── battery_cycles.db      # SQLite database (created automatically)
├── battery_tracker.log    # Log file (created by cron jobs)
└── README.md              # This file
```

## Troubleshooting

### Permission Issues
If you get permission errors accessing battery information:
```bash
# Ensure your terminal has full disk access in System Preferences > Security & Privacy
```

### Python Virtual Environment
If you have issues with dependencies:
```bash
# Remove and recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Issues
If you encounter database errors:
```bash
# Check database permissions
ls -la battery_cycles.db

# Reset database (WARNING: deletes all data)
rm battery_cycles.db
python3 battery_tracker.py --record
```

### Web Server Issues
If the web server won't start:
```bash
# Check if port 5000 is in use
lsof -i :5000

# Use a different port
python3 -c "from app import app; app.run(port=5001)"
```

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

This project is open source and available under the MIT License.

## Technical Notes

### Data Collection Methods

The application uses two methods to extract battery information:

1. **system_profiler**: Primary method using `system_profiler SPPowerDataType`
2. **ioreg**: Fallback method using `ioreg -r -c "AppleSmartBattery"`

### Battery Health Calculation

Battery health percentage is calculated as:
```
Health % = (Current Max Capacity / Original Design Capacity) × 100
```

### Data Storage

- Data is stored locally in SQLite database
- No external dependencies or cloud services required
- Data remains private on your machine
- Database can be backed up by copying the `.db` file

### Performance

- Lightweight Python scripts with minimal system impact
- Web dashboard uses modern JavaScript with Chart.js for smooth visualizations
- Database queries are optimized with proper indexing
- Cron jobs run quickly without affecting system performance

---

**Happy battery monitoring!** 🔋✨