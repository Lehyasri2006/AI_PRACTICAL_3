from models.tank import Tank

_tank_instance = None

def get_tank():
    """Retrieve the global singleton instance of the simulated Tank."""
    global _tank_instance
    if _tank_instance is None:
        _tank_instance = Tank(capacity=200)
    return _tank_instance
