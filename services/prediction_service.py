import time

def calculate_predictions(tank):
    """
    Analyzes historical tank events to generate trends, estimated fill/drain times, 
    and overflow risk levels. Returns INSUFFICIENT_DATA if history is too sparse.
    """
    history = tank.history
    current_level = tank.current_level
    capacity = tank.capacity
    
    # We require at least 3 events to calculate rates and trends
    if len(history) < 3:
        return {
            "trend": "STABLE",
            "estimated_time_until_full": "N/A",
            "estimated_time_until_empty": "N/A",
            "overflow_risk": {
                "level": "LOW",
                "score": 0.0
            },
            "data_sufficiency": "INSUFFICIENT_DATA",
            "recommendation": "Awaiting more telemetry events to build analytical predictions."
        }
        
    # Calculate average fill and drain rates
    fill_rates = []
    drain_rates = []
    
    for i in range(1, len(history)):
        e = history[i]
        prev_e = history[i-1]
        dt = e["timestamp"] - prev_e["timestamp"]
        
        # Clamp dt to avoid division by zero (typical simulation loop is 2.0s)
        if dt < 0.1:
            dt = 2.0
            
        if e["event_type"] == "FILL":
            fill_rates.append(abs(e["amount"]) / dt)
        elif e["event_type"] == "DRAIN":
            drain_rates.append(abs(e["amount"]) / dt)
            
    avg_fill_rate = sum(fill_rates) / len(fill_rates) if fill_rates else 50.0 # L/sec
    avg_drain_rate = sum(drain_rates) / len(drain_rates) if drain_rates else 50.0 # L/sec
    
    # Determine trend over last 3 events
    recent = history[-3:]
    level_diff = recent[-1]["new_level"] - recent[0]["previous_level"]
    
    if level_diff > 10:
        trend = "RISING"
    elif level_diff < -10:
        trend = "FALLING"
    else:
        trend = "STABLE"
        
    estimated_time_until_full = "N/A"
    estimated_time_until_empty = "N/A"
    overflow_risk_level = "LOW"
    overflow_risk_score = 0.0
    
    if trend == "RISING":
        # Calculate time in seconds
        if current_level < capacity:
            time_sec = (capacity - current_level) / avg_fill_rate
            if time_sec < 60:
                estimated_time_until_full = f"{int(time_sec)} seconds"
            else:
                estimated_time_until_full = f"{int(time_sec // 60)}m {int(time_sec % 60)}s"
                
            # Compute overflow risk
            if time_sec < 10:
                overflow_risk_level = "CRITICAL"
                overflow_risk_score = 0.95
            elif time_sec < 30:
                overflow_risk_level = "HIGH"
                overflow_risk_score = 0.80
            elif time_sec < 60:
                overflow_risk_level = "MEDIUM"
                overflow_risk_score = 0.50
            else:
                overflow_risk_level = "LOW"
                overflow_risk_score = 0.20
        else:
            estimated_time_until_full = "0 seconds (Full)"
            overflow_risk_level = "HIGH"
            overflow_risk_score = 0.85
            
    elif trend == "FALLING":
        if current_level > 0:
            time_sec = current_level / avg_drain_rate
            if time_sec < 60:
                estimated_time_until_empty = f"{int(time_sec)} seconds"
            else:
                estimated_time_until_empty = f"{int(time_sec // 60)}m {int(time_sec % 60)}s"
        else:
            estimated_time_until_empty = "0 seconds (Empty)"
            
    # Generate recommendations
    if overflow_risk_level in ["CRITICAL", "HIGH"]:
        recommendation = "Reduce inflow or prepare automatic shutoff immediately."
    elif trend == "FALLING" and current_level < 50:
        recommendation = "Low water level. Initiate fill sequence."
    elif trend == "STABLE":
        recommendation = "System stable. Operations normal."
    else:
        recommendation = "Inflow rate is balanced. Monitor level closely."
        
    return {
        "trend": trend,
        "estimated_time_until_full": estimated_time_until_full,
        "estimated_time_until_empty": estimated_time_until_empty,
        "overflow_risk": {
            "level": overflow_risk_level,
            "score": overflow_risk_score
        },
        "data_sufficiency": "SUFFICIENT",
        "recommendation": recommendation
    }
