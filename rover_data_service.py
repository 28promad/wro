# rover_data_service.py
# Shared data service for real-time sensor data
# Used for inter-process communication between main_pi.py and web_app.py

import threading
import json
import time
from collections import deque
from datetime import datetime

class RoverDataService:
    """Thread-safe shared data buffer for real-time rover sensor telemetry."""
    
    def __init__(self, max_history=300):
        """
        Initialize the data service.
        
        Args:
            max_history: Maximum number of historical readings to keep in memory
        """
        self.lock = threading.RLock()
        self.max_history = max_history
        
        # Current state (latest reading)
        self.current_data = {
            "timestamp": None,
            "co2": None, "voc": None, "temp": None, "hum": None,
            "ax": None, "ay": None, "az": None,
            "gx": None, "gy": None, "gz": None,
            "pos_x": None, "pos_y": None, "yaw": None,
            "connected": False
        }
        
        # Historical data (for graphs)
        self.history = deque(maxlen=max_history)
        
        # Listener callbacks
        self.listeners = []
        
    def update(self, data):
        """
        Update the current sensor data.
        Thread-safe method to be called by main_pi.py.
        
        Args:
            data: Dictionary with sensor readings
        """
        with self.lock:
            self.current_data.update(data)
            self.current_data["timestamp"] = datetime.now().isoformat()
            
            # Add to history
            self.history.append(dict(self.current_data))
            
            # Notify all listeners
            self._notify_listeners()
    
    def set_connected(self, connected):
        """Set the connection status."""
        with self.lock:
            self.current_data["connected"] = connected
            self.current_data["timestamp"] = datetime.now().isoformat()
            self._notify_listeners()
    
    def get_current(self):
        """
        Get the latest sensor data.
        Returns a copy to avoid threading issues.
        """
        with self.lock:
            return dict(self.current_data)
    
    def get_history(self, limit=None):
        """
        Get historical sensor data.
        
        Args:
            limit: Maximum number of records to return (None = all)
            
        Returns:
            List of historical readings
        """
        with self.lock:
            if limit:
                return list(self.history)[-limit:]
            return list(self.history)
    
    def get_graph_data(self, limit=100):
        """
        Get formatted data for graph visualization.
        Returns time-series data for each sensor.
        
        Args:
            limit: Number of recent readings to include
            
        Returns:
            Dictionary with arrays of {time, value} for each sensor
        """
        with self.lock:
            history = list(self.history)[-limit:]
            
            if not history:
                return {
                    "co2": [], "voc": [], "temp": [], "hum": [],
                    "pos_x": [], "pos_y": [], "yaw": [],
                    "ax": [], "ay": [], "az": [],
                    "gx": [], "gy": [], "gz": []
                }
            
            # Extract time-series for each field
            graph_data = {}
            for field in ["co2", "voc", "temp", "hum", "pos_x", "pos_y", "yaw", "ax", "ay", "az", "gx", "gy", "gz"]:
                graph_data[field] = [
                    {
                        "time": record["timestamp"],
                        "value": record.get(field)
                    }
                    for record in history if record.get(field) is not None
                ]
            
            return graph_data
    
    def add_listener(self, callback):
        """
        Register a callback to be notified when data updates.
        Useful for WebSocket connections.
        
        Args:
            callback: Function to call on data update (receives current_data dict)
        """
        with self.lock:
            self.listeners.append(callback)
    
    def _notify_listeners(self):
        """Internal method to notify all registered listeners."""
        for listener in self.listeners:
            try:
                listener(dict(self.current_data))
            except Exception as e:
                print(f"Error notifying listener: {e}")


# Global singleton instance
_instance = None

def get_service():
    """Get or create the global data service instance."""
    global _instance
    if _instance is None:
        _instance = RoverDataService()
    return _instance
