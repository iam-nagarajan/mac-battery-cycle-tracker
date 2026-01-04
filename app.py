#!/usr/bin/env python3
"""
Flask Web Server for Battery Cycle Tracker

This Flask application provides a web interface and API endpoints
for the Mac Battery Cycle Tracker.
"""

from flask import Flask, render_template, jsonify, request
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from battery_tracker import BatteryTracker

# Configure SQLite to use ISO format for datetime
sqlite3.register_adapter(datetime, lambda x: x.isoformat())
sqlite3.register_converter("DATETIME", lambda x: datetime.fromisoformat(x.decode()))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', '')

# Initialize battery tracker
tracker = BatteryTracker()


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/current')
def api_current():
    """API endpoint to get current battery information."""
    try:
        battery_info = tracker.get_battery_info()
        if battery_info:
            return jsonify({
                'success': True,
                'data': battery_info,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not retrieve battery information'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history')
def api_history():
    """API endpoint to get battery cycle history."""
    try:
        days = request.args.get('days', 30, type=int)

        # Limit days to reasonable range
        days = max(1, min(days, 365))

        history = tracker.get_battery_history(days)

        return jsonify({
            'success': True,
            'data': history,
            'days': days
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/record', methods=['POST'])
def api_record():
    """API endpoint to record current battery cycle."""
    try:
        success = tracker.record_battery_cycle()

        if success:
            return jsonify({
                'success': True,
                'message': 'Battery cycle recorded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No new data to record'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats')
def api_stats():
    """API endpoint to get battery statistics."""
    try:
        days = request.args.get('days', 30, type=int)

        # Limit days to reasonable range
        days = max(1, min(days, 365))

        conn = sqlite3.connect(tracker.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()

        # Get total records
        cursor.execute("SELECT COUNT(*) FROM battery_cycles")
        total_records = cursor.fetchone()[0]

        # Get first and last record
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp), 
                   MIN(cycle_count), MAX(cycle_count)
            FROM battery_cycles
        """)
        first_timestamp, last_timestamp, min_cycles, max_cycles = cursor.fetchone()

        # Get average cycles per day if we have enough data
        cycles_per_day = 0
        if first_timestamp and last_timestamp and min_cycles and max_cycles:
            if isinstance(first_timestamp, datetime):
                start_date = first_timestamp
                end_date = last_timestamp
            else:
                start_date = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
            days_diff = (end_date - start_date).days

            if days_diff > 0:
                cycles_per_day = (max_cycles - min_cycles) / days_diff

        # Get recent trend (last 7 days)
        cursor.execute("""
            SELECT cycle_count, timestamp FROM battery_cycles 
            WHERE timestamp >= datetime('now', '-7 days')
            ORDER BY timestamp ASC
        """)
        recent_data = cursor.fetchall()

        trend = "stable"
        if len(recent_data) >= 2:
            first_recent = recent_data[0][0]
            last_recent = recent_data[-1][0]
            if last_recent > first_recent:
                trend = "increasing"
            elif last_recent < first_recent:
                trend = "decreasing"

        # Calculate days between cycle count increments (filtered by time range)
        cursor.execute("""
            SELECT timestamp, cycle_count 
            FROM battery_cycles 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp ASC
        """.format(days))
        all_records = cursor.fetchall()

        days_between_increments = []
        prev_cycle = None
        prev_timestamp = None

        for record in all_records:
            record_timestamp = record[0]
            record_cycle = record[1]

            # Convert timestamp to datetime if needed
            if not isinstance(record_timestamp, datetime):
                if isinstance(record_timestamp, str):
                    try:
                        record_timestamp = datetime.fromisoformat(record_timestamp.replace('Z', '+00:00'))
                    except:
                        continue
                else:
                    continue

            if prev_cycle is not None:
                if record_cycle > prev_cycle:
                    # Cycle count has increased - calculate days since first occurrence of previous cycle count
                    if prev_timestamp and isinstance(prev_timestamp, datetime):
                        days_diff = (record_timestamp - prev_timestamp).total_seconds() / 86400.0
                        days_between_increments.append(days_diff)
                    # Update to new cycle count and timestamp (first occurrence of new cycle count)
                    prev_cycle = record_cycle
                    prev_timestamp = record_timestamp
                elif record_cycle < prev_cycle:
                    # Cycle count decreased (shouldn't happen, but handle it)
                    prev_cycle = record_cycle
                    prev_timestamp = record_timestamp
                # If record_cycle == prev_cycle, don't update - keep prev_timestamp pointing to first occurrence
            else:
                # First record - initialize
                prev_cycle = record_cycle
                prev_timestamp = record_timestamp

        # Calculate statistics
        avg_days = None
        max_days = None
        min_days = None

        if days_between_increments:
            avg_days = sum(days_between_increments) / len(days_between_increments)
            max_days = max(days_between_increments)
            min_days = min(days_between_increments)

        conn.close()

        stats = {
            'total_records': total_records,
            'first_record': first_timestamp.isoformat() if isinstance(first_timestamp, datetime) else first_timestamp,
            'last_record': last_timestamp.isoformat() if isinstance(last_timestamp, datetime) else last_timestamp,
            'min_cycle_count': min_cycles,
            'max_cycle_count': max_cycles,
            'cycles_per_day': round(cycles_per_day, 2),
            'recent_trend': trend,
            'avg_days_per_cycle': round(avg_days, 2) if avg_days is not None else None,
            'max_days_per_cycle': round(max_days, 2) if max_days is not None else None,
            'min_days_per_cycle': round(min_days, 2) if min_days is not None else None
        }

        return jsonify({
            'success': True,
            'data': stats,
            'days': days
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)

    print("Starting Battery Cycle Tracker Web Server...")
    print("Access the dashboard at: http://localhost:5000")
    print("API endpoints available at:")
    print("  GET /api/current - Current battery info")
    print("  GET /api/history?days=30 - Battery history")
    print("  POST /api/record - Record current cycle")
    print("  GET /api/stats - Battery statistics")

    app.run(debug=False, host='0.0.0.0', port=5000)