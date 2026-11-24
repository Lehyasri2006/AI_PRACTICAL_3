from providers.simulation_sensor import SimulationSensorProvider
from providers.iot_sensor import IoTSensorProvider
from services.tank_service import get_tank

# Globals for service state
active_mode = "SIMULATION"
readings_history = []
simulation_provider = None
iot_provider = None

def get_sensor_service_state():
    """Returns the current state and providers of the sensor service."""
    global active_mode, simulation_provider, iot_provider
    tank = get_tank()
    if simulation_provider is None:
        simulation_provider = SimulationSensorProvider(tank)
    if iot_provider is None:
        iot_provider = IoTSensorProvider()
    return active_mode, simulation_provider, iot_provider

def set_sensor_mode(mode):
    """Switch active operating mode between SIMULATION and SENSOR."""
    global active_mode, readings_history
    if mode not in ["SIMULATION", "SENSOR"]:
        raise ValueError("Invalid mode. Allowed: SIMULATION, SENSOR")
    active_mode = mode
    readings_history.clear() # Reset noise-smoothing buffers on mode transitions

def process_sensor_telemetry(raw_distance):
    """
    Validates physical distance values, applies a rolling average filter,
    calculates corresponding water volume, and returns a quality summary.
    """
    global readings_history
    tank = get_tank()
    capacity = tank.capacity
    
    # 1. Validation checks
    if not isinstance(raw_distance, (int, float)):
        return {
            "raw_value": None,
            "filtered_value": None,
            "estimated_level": None,
            "sensor_status": "INVALID",
            "data_quality": "BAD",
            "warning_message": "Non-numeric sensor distance reading."
        }
        
    if raw_distance < 0.0 or raw_distance > 100.0:
        return {
            "raw_value": raw_distance,
            "filtered_value": None,
            "estimated_level": None,
            "sensor_status": "INVALID",
            "data_quality": "BAD",
            "warning_message": f"Distance {raw_distance}cm out of bounds (0-100cm)."
        }
        
    # Check for unrealistic sudden jumps (>50cm change compared to previous reading)
    if readings_history:
        prev_filtered = sum(readings_history) / len(readings_history)
        if abs(raw_distance - prev_filtered) > 50.0:
            return {
                "raw_value": raw_distance,
                "filtered_value": prev_filtered,
                "sensor_status": "NOISY",
                "data_quality": "POOR",
                "warning_message": "Sudden telemetry delta detected. Filtering spike."
            }

    # 2. Smooth readings with rolling average (window of 5)
    readings_history.append(raw_distance)
    if len(readings_history) > 5:
        readings_history.pop(0)
        
    filtered_distance = sum(readings_history) / len(readings_history)
    
    # 3. Convert distance to level
    # 100cm represents empty (0L), 0cm represents full (capacity L)
    height_fraction = (100.0 - filtered_distance) / 100.0
    height_fraction = max(0.0, min(1.0, height_fraction)) # Clamp
    
    estimated_level = round(height_fraction * capacity, 1)
    
    return {
        "raw_value": round(raw_distance, 2),
        "filtered_value": round(filtered_distance, 2),
        "estimated_level": estimated_level,
        "sensor_status": "NORMAL",
        "data_quality": "GOOD",
        "warning_message": None
    }
