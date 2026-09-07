import time

def get_radar_url():
    # RainViewer liefert Radar-Bilder als PNG
    # Wir nutzen das "Europe" Radar, das Deutschland perfekt abdeckt.
    timestamp = int(time.time())
    return f"https://tilecache.rainviewer.com/v2/radar/256/0/0/0/0/0.png?{timestamp}"
