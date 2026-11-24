from flask import Blueprint, request, jsonify, render_template
from services.tank_service import get_tank
from services.prediction_service import calculate_predictions
from services.anomaly_service import detect_anomalies
from services.sensor_service import (
    get_sensor_service_state,
    set_sensor_mode,
    process_sensor_telemetry
)
from algorithms.dls import run_dls

tank_bp = Blueprint('tank', __name__)

def success_response(data, message="Operation completed successfully", status_code=200):
    return jsonify({
        "success": True,
        "data": data,
        "message": message
    }), status_code

def error_response(code, message, status_code=400):
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }), status_code

@tank_bp.route('/')
def index():
    """Renders the Digital Twin Control Center HTML dashboard."""
    return render_template('index.html')

@tank_bp.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current simulated tank state, active sensor inputs, and hardware connectivity."""
    tank = get_tank()
    active_mode, sim_provider, iot_provider = get_sensor_service_state()
    
    # Retrieve distance reading depending on the active mode
    try:
        if active_mode == "SIMULATION":
            distance = sim_provider.read_distance()
            sensor_hardware = sim_provider.get_status()
        else:
            distance = iot_provider.read_distance()
            sensor_hardware = iot_provider.get_status()
            
        telemetry = process_sensor_telemetry(distance)
        
        # In SENSOR mode, the physical telemetry directly drives the tank volume level
        if active_mode == "SENSOR" and telemetry["sensor_status"] == "NORMAL":
            previous = tank.current_level
            new_level = telemetry["estimated_level"]
            tank.current_level = new_level
            if previous != new_level:
                tank._record_event("SENSOR_READING", previous, new_level, new_level - previous, "SENSOR")
                
    except Exception as e:
        telemetry = {
            "raw_value": None,
            "filtered_value": None,
            "estimated_level": None,
            "sensor_status": "ERROR",
            "data_quality": "BAD",
            "warning_message": f"Sensor read exception: {str(e)}"
        }
        sensor_hardware = {
            "sensor_id": "IOT_NODE_UNKNOWN",
            "provider_type": "IOT_HARDWARE",
            "sensor_status": "DISCONNECTED",
            "data_quality": "BAD",
            "warning_message": str(e)
        }

    tank_status = tank.get_status()
    tank_status["operating_mode"] = active_mode
    
    response_data = {
        "tank": tank_status,
        "sensor": telemetry,
        "sensor_hardware": sensor_hardware
    }
    
    return success_response(response_data, "Telemetry status retrieved successfully.")

@tank_bp.route('/api/fill', methods=['POST'])
def fill_tank():
    """Adds a specified amount of water to the tank in simulation mode."""
    tank = get_tank()
    active_mode, _, _ = get_sensor_service_state()
    
    if active_mode == "SENSOR":
        return error_response("INVALID_MODE", "Manual filling is disabled in SENSOR mode. Control is driven by telemetry.", 400)
        
    data = request.get_json() or {}
    amount = data.get("amount")
    source = data.get("source", "USER")
    
    if amount is None:
        return error_response("MISSING_FIELD", "Missing 'amount' field in request body.", 400)
        
    try:
        tank.fill(amount, source=source)
        tank_status = tank.get_status()
        tank_status["operating_mode"] = active_mode
        return success_response({"tank": tank_status}, f"Filled tank with {amount} L.")
    except ValueError as e:
        return error_response("INVALID_VALUE", str(e), 400)

@tank_bp.route('/api/drain', methods=['POST'])
def drain_tank():
    """Removes a specified amount of water from the tank in simulation mode."""
    tank = get_tank()
    active_mode, _, _ = get_sensor_service_state()
    
    if active_mode == "SENSOR":
        return error_response("INVALID_MODE", "Manual draining is disabled in SENSOR mode. Control is driven by telemetry.", 400)
        
    data = request.get_json() or {}
    amount = data.get("amount")
    source = data.get("source", "USER")
    
    if amount is None:
        return error_response("MISSING_FIELD", "Missing 'amount' field in request body.", 400)
        
    try:
        tank.drain(amount, source=source)
        tank_status = tank.get_status()
        tank_status["operating_mode"] = active_mode
        return success_response({"tank": tank_status}, f"Drained {amount} L from tank.")
    except ValueError as e:
        return error_response("INVALID_VALUE", str(e), 400)

@tank_bp.route('/api/reset', methods=['POST'])
def reset_tank():
    """Resets the water level of the tank back to 0."""
    tank = get_tank()
    active_mode, _, _ = get_sensor_service_state()
    tank.reset()
    
    tank_status = tank.get_status()
    tank_status["operating_mode"] = active_mode
    return success_response({"tank": tank_status}, "Water tank reset successfully.")

@tank_bp.route('/api/capacity', methods=['POST'])
def update_capacity():
    """Updates target capacity boundaries."""
    tank = get_tank()
    active_mode, _, _ = get_sensor_service_state()
    data = request.get_json() or {}
    capacity = data.get("capacity")
    
    if capacity is None:
        return error_response("MISSING_FIELD", "Missing 'capacity' field in request body.", 400)
        
    try:
        tank.update_capacity(capacity)
        tank_status = tank.get_status()
        tank_status["operating_mode"] = active_mode
        return success_response({"tank": tank_status}, f"Capacity updated to {capacity} L.")
    except ValueError as e:
        return error_response("INVALID_VALUE", str(e), 400)

@tank_bp.route('/api/search', methods=['POST'])
def run_search():
    """Executes a Depth-Limited Search algorithm from an initial state to a target state."""
    tank = get_tank()
    data = request.get_json() or {}
    initial_state = data.get("initial_state")
    target_state = data.get("target_state")
    limit = data.get("depth_limit", 5)
    
    if initial_state is None or target_state is None:
        return error_response("MISSING_FIELD", "Missing 'initial_state' or 'target_state' in request body.", 400)
        
    try:
        limit = int(limit)
        initial_state = int(round(float(initial_state) / 100.0) * 100)
        target_state = int(round(float(target_state) / 100.0) * 100)
    except (ValueError, TypeError):
        return error_response("INVALID_TYPE", "initial_state, target_state, and depth_limit must be numeric values.", 400)
        
    # Validation checks on states
    if initial_state < 0 or initial_state > tank.capacity:
        initial_state = max(0, min(initial_state, tank.capacity))
    if target_state < 0 or target_state > tank.capacity:
        target_state = max(0, min(target_state, tank.capacity))
        
    search_results = run_dls(initial_state, target_state, limit, tank.capacity)
    return success_response({"dls": search_results}, "Depth-Limited Search completed.")

@tank_bp.route('/api/intelligence', methods=['GET'])
def get_intelligence():
    """Computes transparent consumption analysis and transition anomalies."""
    tank = get_tank()
    predictions = calculate_predictions(tank)
    anomalies = detect_anomalies(tank)
    
    intelligence_data = {
        "predictions": predictions,
        "anomalies": anomalies
    }
    return success_response({"intelligence": intelligence_data}, "System intelligence reports compiled.")

@tank_bp.route('/api/sensor-reading', methods=['POST'])
def post_sensor_reading():
    """Receives physical ultrasonic level measurements from external IoT hardware."""
    _, _, iot_provider = get_sensor_service_state()
    data = request.get_json() or {}
    distance_cm = data.get("distance_cm")
    
    if distance_cm is None:
        return error_response("MISSING_FIELD", "Missing 'distance_cm' in request body.", 400)
        
    try:
        distance_cm = float(distance_cm)
    except (ValueError, TypeError):
        return error_response("INVALID_TYPE", "Distance must be a numeric value.", 400)
        
    if distance_cm < 0.0 or distance_cm > 100.0:
        return error_response("OUT_OF_BOUNDS", "Ultrasonic distance sensor bounds are 0-100cm.", 400)
        
    iot_provider.update_reading(distance_cm)
    
    # Run a dry processing run for immediate validation
    telemetry = process_sensor_telemetry(distance_cm)
    
    return success_response({"sensor": telemetry}, "IoT Sensor reading received successfully.")

@tank_bp.route('/api/mode', methods=['POST'])
def change_mode():
    """Sets the operational mode of the system (SIMULATION vs SENSOR)."""
    data = request.get_json() or {}
    mode = data.get("mode")
    
    if not mode:
        return error_response("MISSING_FIELD", "Missing 'mode' in request body.", 400)
        
    try:
        set_sensor_mode(mode)
        tank = get_tank()
        tank_status = tank.get_status()
        tank_status["operating_mode"] = mode
        return success_response({"tank": tank_status}, f"System switched to {mode} mode.")
    except ValueError as e:
        return error_response("INVALID_VALUE", str(e), 400)
