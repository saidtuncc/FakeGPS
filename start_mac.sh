#!/bin/bash
# FakeGPS Pro — macOS Başlatma Scripti

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║      📍 FakeGPS Pro                  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Python kontrol
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python3 bulunamadı!"
    echo "  → https://python.org adresinden indir"
    exit 1
fi

echo "  ✅ Python3 bulundu: $(python3 --version)"

# Bağımlılık kontrol ve kurulum
echo "  📦 Bağımlılıklar kontrol ediliyor..."
python3 -c "import flask" 2>/dev/null || {
    echo "  📥 Flask kuruluyor..."
    pip3 install flask
}
python3 -c "import pymobiledevice3" 2>/dev/null || {
    echo "  📥 pymobiledevice3 kuruluyor..."
    pip3 install pymobiledevice3
}

echo ""
echo "  🚀 FakeGPS Pro başlatılıyor..."
echo "  📱 Tarayıcıda açılacak: http://127.0.0.1:5555"
echo ""
echo "  ⚠️  Önce ayrı bir terminalde tunnel başlat:"
echo "  sudo python3 -m pymobiledevice3 remote start-tunnel --protocol tcp"
echo ""

# Tarayıcıyı aç
sleep 1
open http://127.0.0.1:5555 &

# Uygulamayı başlat
cd "$(dirname "$0")"
python3 fakegps_app.py
