#!/usr/bin/env python3
"""
FakeGPS Pro — Premium Konum Simülasyon Aracı
Flask backend + pymobiledevice3 subprocess entegrasyonu
"""

from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import time
import math
import json
import sys
import os

app = Flask(__name__)
PYTHON = sys.executable  # Windows/Mac uyumlu

# ─────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────
state = {
    'rsd_address': '',
    'rsd_port': '',
    'connected': False,
    'device_name': '',
    'device_model': '',
    'device_ios': '',
    'current_lat': 0.0,
    'current_lon': 0.0,
    'simulating': False,
    'route_running': False,
    'route_paused': False,
    'route_progress': 0,
    'route_total_distance': 0,
}

location_process = None
location_lock = threading.Lock()
route_thread = None
route_stop_event = threading.Event()
route_pause_event = threading.Event()


# ─────────────────────────────────────────────
# Location Management (subprocess)
# ─────────────────────────────────────────────
def set_location(lat, lon):
    global location_process
    with location_lock:
        if location_process and location_process.poll() is None:
            try:
                location_process.terminate()
                location_process.wait(timeout=3)
            except Exception:
                try:
                    location_process.kill()
                except Exception:
                    pass

        cmd = [
            PYTHON, '-m', 'pymobiledevice3',
            'developer', 'dvt', 'simulate-location', 'set',
            '--rsd', state['rsd_address'], str(state['rsd_port']),
            '--', str(lat), str(lon)
        ]
        location_process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        state['current_lat'] = lat
        state['current_lon'] = lon
        state['simulating'] = True


def clear_location():
    global location_process
    with location_lock:
        if location_process and location_process.poll() is None:
            try:
                location_process.terminate()
                location_process.wait(timeout=3)
            except Exception:
                try:
                    location_process.kill()
                except Exception:
                    pass
        location_process = None

        try:
            cmd = [
                PYTHON, '-m', 'pymobiledevice3',
                'developer', 'dvt', 'simulate-location', 'clear',
                '--rsd', state['rsd_address'], str(state['rsd_port'])
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
        except Exception:
            pass

        state['current_lat'] = 0.0
        state['current_lon'] = 0.0
        state['simulating'] = False


# ─────────────────────────────────────────────
# Route Simulation
# ─────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def simulate_route(points, speed_kmh):
    speed_ms = speed_kmh / 3.6
    update_interval = 2.5

    total_points = len(points)
    if total_points < 2:
        state['route_running'] = False
        return

    total_dist = sum(
        haversine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        for i in range(total_points - 1)
    )
    state['route_total_distance'] = total_dist
    state['route_running'] = True
    state['route_paused'] = False
    state['route_progress'] = 0

    traveled = 0

    for i in range(total_points - 1):
        if route_stop_event.is_set():
            break

        s_lat, s_lon = points[i]
        e_lat, e_lon = points[i + 1]
        seg_dist = haversine(s_lat, s_lon, e_lat, e_lon)

        if seg_dist < 0.5:
            traveled += seg_dist
            continue

        duration = seg_dist / speed_ms
        steps = max(1, int(duration / update_interval))

        for step in range(steps + 1):
            if route_stop_event.is_set():
                break

            while route_pause_event.is_set() and not route_stop_event.is_set():
                time.sleep(0.3)

            t = step / max(steps, 1)
            lat = s_lat + (e_lat - s_lat) * t
            lon = s_lon + (e_lon - s_lon) * t

            try:
                set_location(lat, lon)
            except Exception as e:
                print(f"  ⚠️ Konum hatası: {e}")

            traveled += seg_dist / max(steps, 1)
            state['route_progress'] = min(100, (traveled / max(total_dist, 1)) * 100)

            if step < steps and not route_stop_event.is_set():
                time.sleep(update_interval)

    state['route_running'] = False
    if not route_stop_event.is_set():
        state['route_progress'] = 100


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/detect_device', methods=['GET'])
def detect_device():
    try:
        result = subprocess.run(
            [PYTHON, '-m', 'pymobiledevice3', 'usbmux', 'list'],
            capture_output=True, text=True, timeout=10
        )
        devices = json.loads(result.stdout)
        if devices:
            d = devices[0]
            state['device_name'] = d.get('DeviceName', 'Unknown')
            state['device_model'] = d.get('ProductType', 'Unknown')
            state['device_ios'] = d.get('ProductVersion', 'Unknown')
            return jsonify({
                'success': True,
                'device': {
                    'name': d.get('DeviceName', 'Unknown'),
                    'model': d.get('ProductType', 'Unknown'),
                    'ios': d.get('ProductVersion', 'Unknown'),
                    'udid': d.get('Identifier', ''),
                    'connection': d.get('ConnectionType', 'Unknown'),
                }
            })
        return jsonify({'success': False, 'error': 'Cihaz bulunamadı.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/connect', methods=['POST'])
def connect():
    data = request.json
    state['rsd_address'] = data.get('rsd_address', '')
    state['rsd_port'] = data.get('rsd_port', '')
    state['connected'] = True
    return jsonify({'success': True})


@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    clear_location()
    state['connected'] = False
    return jsonify({'success': True})


@app.route('/api/location/set', methods=['POST'])
def api_set_location():
    if not state['connected']:
        return jsonify({'success': False, 'error': 'Bağlı değil.'})
    data = request.json
    lat, lon = float(data['lat']), float(data['lon'])
    try:
        set_location(lat, lon)
        return jsonify({'success': True, 'lat': lat, 'lon': lon})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/location/clear', methods=['POST'])
def api_clear_location():
    try:
        clear_location()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/route/start', methods=['POST'])
def api_route_start():
    global route_thread
    if not state['connected']:
        return jsonify({'success': False, 'error': 'Bağlı değil.'})

    data = request.json
    points = data['points']
    speed = float(data.get('speed', 5))

    if len(points) < 2:
        return jsonify({'success': False, 'error': 'En az 2 nokta gerekli.'})

    route_stop_event.set()
    if route_thread and route_thread.is_alive():
        route_thread.join(timeout=5)

    route_stop_event.clear()
    route_pause_event.clear()

    route_thread = threading.Thread(
        target=simulate_route, args=(points, speed), daemon=True
    )
    route_thread.start()
    return jsonify({'success': True})


@app.route('/api/route/pause', methods=['POST'])
def api_route_pause():
    if route_pause_event.is_set():
        route_pause_event.clear()
        state['route_paused'] = False
    else:
        route_pause_event.set()
        state['route_paused'] = True
    return jsonify({'success': True, 'paused': state['route_paused']})


@app.route('/api/route/stop', methods=['POST'])
def api_route_stop():
    route_stop_event.set()
    route_pause_event.clear()
    state['route_running'] = False
    state['route_paused'] = False
    return jsonify({'success': True})


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        'connected': state['connected'],
        'simulating': state['simulating'],
        'lat': state['current_lat'],
        'lon': state['current_lon'],
        'route_running': state['route_running'],
        'route_paused': state['route_paused'],
        'route_progress': state['route_progress'],
        'route_total_distance': state['route_total_distance'],
        'device_name': state['device_name'],
    })


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("\n")
    print("  ╔══════════════════════════════════════╗")
    print("  ║      📍 FakeGPS Pro v1.0             ║")
    print("  ║      http://127.0.0.1:5555           ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"\n  Python: {PYTHON}")
    print("  Tarayıcıda aç: http://127.0.0.1:5555\n")
    app.run(host='127.0.0.1', port=5555, debug=False)
