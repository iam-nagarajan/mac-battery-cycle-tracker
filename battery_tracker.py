#!/usr/bin/env python3
"""
Mac Battery Cycle Count Tracker

This script reads the battery cycle count from macOS and stores it in a SQLite database
with timestamps for trend analysis.
"""

import subprocess
import sqlite3
import datetime
import re
from pathlib import Path
from typing import Optional, Dict, Any

# Configure SQLite to use ISO format for datetime
sqlite3.register_adapter(datetime.datetime, lambda x: x.isoformat())
sqlite3.register_converter("DATETIME", lambda x: datetime.datetime.fromisoformat(x.decode()))


class BatteryTracker:
    def __init__(self, db_path: str = "battery_cycles.db"):
        """Initialize the battery tracker with a database path."""
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self) -> None:
        """Initialize the SQLite database with the battery_cycles table."""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battery_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cycle_count INTEGER NOT NULL,
                max_capacity INTEGER,
                design_capacity INTEGER,
                health_percentage REAL,
                battery_condition TEXT,
                charge_remaining REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster timestamp queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON battery_cycles(timestamp)
        """)
        
        conn.commit()
        conn.close()

    def get_battery_info_system_profiler(self) -> Optional[Dict[str, Any]]:
        """Get battery information using system_profiler command."""
        try:
            # Run system_profiler to get power data
            result = subprocess.run(
                ["system_profiler", "SPPowerDataType"],
                capture_output=True,
                text=True,
                check=True
            )
            
            battery_info = {}
            lines = result.stdout.split('\n')
            
            # Parse relevant battery information
            for line in lines:
                line = line.strip()
                if "Cycle Count:" in line:
                    battery_info['cycle_count'] = int(re.search(r'(\d+)', line).group(1))
                elif "Full Charge Capacity (mAh):" in line:
                    battery_info['max_capacity'] = int(re.search(r'(\d+)', line).group(1))
                elif "Design Capacity (mAh):" in line:
                    battery_info['design_capacity'] = int(re.search(r'(\d+)', line).group(1))
                elif "Maximum Capacity:" in line:
                    # Extract percentage value (e.g., "Maximum Capacity: 97%" -> 97.0)
                    match = re.search(r'(\d+)%', line)
                    if match:
                        battery_info['health_percentage'] = float(match.group(1))
                elif "Condition:" in line:
                    battery_info['battery_condition'] = line.split(":")[-1].strip()
                elif "Charge Remaining (mAh):" in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        battery_info['charge_remaining'] = int(match.group(1))
            
            # Calculate health percentage if we have both raw capacities (fallback method)
            if 'max_capacity' in battery_info and 'design_capacity' in battery_info and 'health_percentage' not in battery_info:
                battery_info['health_percentage'] = (
                    battery_info['max_capacity'] / battery_info['design_capacity'] * 100
                )
            
            return battery_info
            
        except subprocess.CalledProcessError as e:
            print(f"Error running system_profiler: {e}")
            return None
        except Exception as e:
            print(f"Error parsing system_profiler output: {e}")
            return None

    def get_battery_info_ioreg(self) -> Optional[Dict[str, Any]]:
        """Get battery information using ioreg command as fallback."""
        try:
            result = subprocess.run(
                ["ioreg", "-r", "-c", "AppleSmartBattery"],
                capture_output=True,
                text=True,
                check=True
            )
            
            battery_info = {}
            
            # Look for cycle count
            cycle_match = re.search(r'"CycleCount" = (\d+)', result.stdout)
            if cycle_match:
                battery_info['cycle_count'] = int(cycle_match.group(1))
            
            # Look for max capacity (percentage)
            max_cap_match = re.search(r'"MaxCapacity" = (\d+)', result.stdout)
            if max_cap_match:
                max_cap_percent = int(max_cap_match.group(1))
                if max_cap_percent <= 100:  # This is likely a percentage
                    battery_info['health_percentage'] = float(max_cap_percent)
            
            # Look for design capacity
            design_cap_match = re.search(r'"DesignCapacity" = (\d+)', result.stdout)
            if design_cap_match:
                battery_info['design_capacity'] = int(design_cap_match.group(1))
            
            # Look for actual current max capacity in mAh
            raw_max_cap_match = re.search(r'"AppleRawMaxCapacity" = (\d+)', result.stdout)
            if raw_max_cap_match:
                battery_info['max_capacity'] = int(raw_max_cap_match.group(1))

            # Calculate health percentage from raw values if not already set
            if ('max_capacity' in battery_info and 'design_capacity' in battery_info
                and 'health_percentage' not in battery_info):
                battery_info['health_percentage'] = (
                    battery_info['max_capacity'] / battery_info['design_capacity'] * 100
                )

            return battery_info
            
        except subprocess.CalledProcessError as e:
            print(f"Error running ioreg: {e}")
            return None
        except Exception as e:
            print(f"Error parsing ioreg output: {e}")
            return None

    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get battery information, trying system_profiler first, then ioreg."""
        battery_info = self.get_battery_info_system_profiler()
        
        if not battery_info or 'cycle_count' not in battery_info:
            print("system_profiler failed, trying ioreg...")
            battery_info = self.get_battery_info_ioreg()
        
        return battery_info

    def record_battery_cycle(self) -> bool:
        """Record the current battery cycle count and info to the database."""
        battery_info = self.get_battery_info()
        
        if not battery_info or 'cycle_count' not in battery_info:
            print("Could not retrieve battery cycle count")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            cursor = conn.cursor()
            
            # Check if we already have a record for today
            today = datetime.date.today().isoformat()
            cursor.execute("""
                SELECT cycle_count, health_percentage FROM battery_cycles 
                WHERE DATE(timestamp) = DATE(?) 
                ORDER BY timestamp DESC LIMIT 1
            """, (today,))
            
            existing_record = cursor.fetchone()
            
            # Only insert if this is a new day, cycle count has changed, or health info is missing
            should_record = False
            if not existing_record:
                should_record = True
                print("No record for today - creating new entry")
            elif existing_record[0] != battery_info['cycle_count']:
                should_record = True
                print(f"Cycle count changed: {existing_record[0]} -> {battery_info['cycle_count']}")
            elif existing_record[1] is None and battery_info.get('health_percentage') is not None:
                should_record = True
                print("Adding missing health information")

            if should_record:
                cursor.execute("""
                    INSERT INTO battery_cycles 
                    (timestamp, cycle_count, max_capacity, design_capacity, health_percentage, 
                     battery_condition, charge_remaining)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.datetime.now(),
                    battery_info['cycle_count'],
                    battery_info.get('max_capacity'),
                    battery_info.get('design_capacity'),
                    battery_info.get('health_percentage'),
                    battery_info.get('battery_condition'),
                    battery_info.get('charge_remaining')
                ))
                
                conn.commit()
                print(f"Recorded battery cycle count: {battery_info['cycle_count']}")
                
                if battery_info.get('health_percentage'):
                    print(f"Battery health: {battery_info['health_percentage']:.1f}%")
                
                return True
            else:
                print(f"No change in cycle count ({battery_info['cycle_count']}) since last record")
                return False
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()

    def get_battery_history(self, days: int = 30) -> list:
        """Get battery cycle history for the specified number of days."""
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, cycle_count, health_percentage, battery_condition
                FROM battery_cycles 
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp ASC
            """.format(days))
            
            records = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'timestamp': record[0].isoformat() if isinstance(record[0], datetime.datetime) else record[0],
                    'cycle_count': record[1],
                    'health_percentage': record[2],
                    'battery_condition': record[3]
                }
                for record in records
            ]
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def print_current_status(self) -> None:
        """Print the current battery status."""
        battery_info = self.get_battery_info()
        
        if battery_info:
            print("\n=== Current Battery Status ===")
            print(f"Cycle Count: {battery_info['cycle_count']}")
            
            if battery_info.get('health_percentage'):
                print(f"Health: {battery_info['health_percentage']:.1f}%")
            
            if battery_info.get('battery_condition'):
                print(f"Condition: {battery_info['battery_condition']}")
            
            if battery_info.get('max_capacity') and battery_info.get('design_capacity'):
                print(f"Capacity: {battery_info['max_capacity']} / {battery_info['design_capacity']} mAh")
            
            if battery_info.get('charge_remaining'):
                print(f"Current Charge: {battery_info['charge_remaining']} mAh")
        else:
            print("Could not retrieve battery information")


def main():
    """Main function to handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mac Battery Cycle Tracker")
    parser.add_argument("--record", action="store_true", 
                       help="Record current battery cycle count")
    parser.add_argument("--status", action="store_true",
                       help="Show current battery status")
    parser.add_argument("--history", type=int, default=30,
                       help="Show battery history for N days (default: 30)")
    parser.add_argument("--db", default="battery_cycles.db",
                       help="Database file path (default: battery_cycles.db)")
    
    args = parser.parse_args()
    
    tracker = BatteryTracker(args.db)
    
    if args.record:
        tracker.record_battery_cycle()
    
    if args.status:
        tracker.print_current_status()
    
    if not args.record and not args.status:
        # Default behavior: record and show status
        tracker.record_battery_cycle()
        tracker.print_current_status()


if __name__ == "__main__":
    main()