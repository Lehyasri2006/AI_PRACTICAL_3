import math

def detect_anomalies(tank):
    """
    Performs transparent anomaly detection by evaluating physical state change
    events against the historical distribution of changes.
    """
    history = tank.history
    
    # 1. Filter out non-physical event history logs (e.g. resets, capacity alterations, DLS search node steps)
    physical_events = [
        e for e in history 
        if e["event_type"] in ["FILL", "DRAIN"] 
        and e["source"] in ["USER", "SIMULATION", "SENSOR", "SYSTEM"]
    ]
    
    # Check boundaries on the latest raw event (in case it is out of limits, e.g. from an invalid fill or sensor spike)
    if history:
        latest_event = history[-1]
        if latest_event["new_level"] < 0 or latest_event["new_level"] > tank.capacity:
            return {
                "anomaly_detected": True,
                "anomaly_type": "IMPOSSIBLE_CHANGE",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "explanation": f"Water level {latest_event['new_level']}L exceeds physical boundaries of the tank."
            }

    # Verify at least 2 valid physical events exist to run comparison checks
    if len(physical_events) < 2:
        return {
            "anomaly_detected": False,
            "anomaly_type": "NONE",
            "severity": "LOW",
            "confidence": 0.0,
            "explanation": "Insufficient physical event history to establish anomaly detection baselines."
        }
        
    latest_physical = physical_events[-1]
    
    # Check for extreme sudden jumps (SENSOR_JUMP) on the latest physical event
    abs_amount = abs(latest_physical["amount"])
    if abs_amount > 250:
        return {
            "anomaly_detected": True,
            "anomaly_type": "SENSOR_JUMP",
            "severity": "HIGH",
            "confidence": 0.95,
            "explanation": f"An instantaneous level change of {abs_amount}L was detected, which is physically unrealistic."
        }

    # We need at least 4 physical events to calculate standard deviation rates comparison
    if len(physical_events) < 4:
        return {
            "anomaly_detected": False,
            "anomaly_type": "NONE",
            "severity": "LOW",
            "confidence": 0.0,
            "explanation": "Insufficient physical event history to establish rate-based anomaly detection baselines."
        }
        
    # Calculate rates of change for all historical physical intervals (excluding the latest physical event)
    rates = []
    for i in range(1, len(physical_events) - 1):
        e = physical_events[i]
        prev_e = physical_events[i-1]
        dt = e["timestamp"] - prev_e["timestamp"]
        if dt < 0.1:
            continue  # Ignore zero or near-zero time intervals
        rates.append(abs(e["amount"]) / dt)
        
    if not rates:
        return {
            "anomaly_detected": False,
            "anomaly_type": "NONE",
            "severity": "LOW",
            "confidence": 0.0,
            "explanation": "No valid physical intervals to compare change rates."
        }
        
    # Statistical properties
    mean_rate = sum(rates) / len(rates)
    variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
    std_dev = math.sqrt(variance)
    
    # Calculate rate of the latest physical event
    latest_dt = latest_physical["timestamp"] - physical_events[-2]["timestamp"]
    if latest_dt < 0.1:
        return {
            "anomaly_detected": False,
            "anomaly_type": "NONE",
            "severity": "LOW",
            "confidence": 0.0,
            "explanation": "Recent change occurred in near-zero time delta. Skipping rate analysis."
        }
        
    latest_rate = abs_amount / latest_dt
    
    # Standard threshold (3 standard deviations, with a minimum noise floor of 25L/sec)
    threshold = max(mean_rate + 3.0 * std_dev, 25.0)
    
    if latest_rate > threshold:
        confidence = min(0.5 + (latest_rate - threshold) / (threshold * 2), 0.99)
        
        if latest_physical["amount"] < 0:
            # Level is dropping abnormally fast without manual command
            return {
                "anomaly_detected": True,
                "anomaly_type": "POSSIBLE_LEAK",
                "severity": "HIGH",
                "confidence": round(confidence, 2),
                "explanation": f"Water level decreased at {round(latest_rate, 2)} L/s, exceeding normal limits."
            }
        else:
            # Level is rising abnormally fast
            return {
                "anomaly_detected": True,
                "anomaly_type": "RAPID_FILL",
                "severity": "MEDIUM",
                "confidence": round(confidence, 2),
                "explanation": f"Water level increased at {round(latest_rate, 2)} L/s, indicating a potential inflow burst."
            }
            
    return {
        "anomaly_detected": False,
        "anomaly_type": "NONE",
        "severity": "LOW",
        "confidence": 0.0,
        "explanation": "Telemetry changes fall within normal statistical bounds."
    }
