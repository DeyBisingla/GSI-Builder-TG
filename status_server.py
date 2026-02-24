#!/usr/bin/env python3
"""
GSI Builder Status Server
Menyediakan endpoint /api/status untuk monitoring build
Berjalan di port 4567 untuk Cloudflare One tunnel
"""

from flask import Flask, jsonify
import json
import os
import threading
import time

app = Flask(__name__)

STATUS_FILE = 'status.json'
DEFAULT_STATUS = {
    "status": "idle",
    "step": "waiting",
    "progress": 0,
    "message": "Menunggu trigger build...",
    "timestamp": None
}

def read_status():
    """Baca status dari file JSON"""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f:
                data = json.load(f)
                data['timestamp'] = int(time.time())
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_STATUS

@app.route('/')
def index():
    """Root endpoint - redirect ke status"""
    return jsonify({
        "service": "GSI Builder Status API",
        "version": "1.0",
        "endpoints": {
            "/api/status": "Get current build status"
        }
    })

@app.route('/api/status')
def api_status():
    """Endpoint utama untuk status build"""
    status = read_status()
    return jsonify(status)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "gsi-builder"})

if __name__ == '__main__':
    # Jalankan di port 4567 untuk Cloudflare One tunnel
    print("[STATUS SERVER] Starting GSI Builder Status Server...")
    print("[STATUS SERVER] Port: 4567")
    print("[STATUS SERVER] Endpoint: http://localhost:4567/api/status")
    
    # Inisialisasi status file jika belum ada
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, 'w') as f:
            json.dump(DEFAULT_STATUS, f, indent=2)
    
    app.run(host='0.0.0.0', port=4567, debug=False)
