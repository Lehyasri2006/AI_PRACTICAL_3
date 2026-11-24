import time

class Tank:
    def __init__(self, capacity=200):
        self.allowed_capacities = [200, 400, 600, 800]
        if capacity not in self.allowed_capacities:
            raise ValueError(f"Invalid capacity. Allowed capacities: {self.allowed_capacities}")
        self.capacity = capacity
        self.current_level = 0
        self.history = []

    def fill(self, amount, source="USER"):
        """Add water to the tank, clamping to capacity."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Fill amount must be a numeric value")
        if amount <= 0:
            raise ValueError("Fill amount must be greater than zero")
        
        previous = self.current_level
        self.current_level = min(self.current_level + amount, self.capacity)
        actual_change = self.current_level - previous
        
        self._record_event("FILL", previous, self.current_level, actual_change, source)
        return self.current_level

    def drain(self, amount, source="USER"):
        """Remove water from the tank, clamping to 0."""
        if not isinstance(amount, (int, float)):
            raise ValueError("Drain amount must be a numeric value")
        if amount <= 0:
            raise ValueError("Drain amount must be greater than zero")
        
        previous = self.current_level
        self.current_level = max(self.current_level - amount, 0)
        actual_change = previous - self.current_level
        
        self._record_event("DRAIN", previous, self.current_level, -actual_change, source)
        return self.current_level

    def reset(self, source="USER"):
        """Reset water level to 0."""
        previous = self.current_level
        self.current_level = 0
        self._record_event("RESET", previous, 0, -previous, source)
        return self.current_level

    def update_capacity(self, new_capacity, source="USER"):
        """Update tank capacity and handle current level adjustments."""
        if new_capacity not in self.allowed_capacities:
            raise ValueError(f"Capacity must be one of {self.allowed_capacities}")
        
        previous_capacity = self.capacity
        previous_level = self.current_level
        self.capacity = new_capacity
        
        # If new capacity is less than current level, water overflows/clamps to new capacity
        if self.current_level > self.capacity:
            self.current_level = self.capacity
            
        self._record_event("CAPACITY_CHANGE", previous_level, self.current_level, new_capacity - previous_capacity, source)
        return self.current_level

    def get_status(self):
        """Return the current state dictionary of the tank."""
        return {
            "water": self.current_level,
            "capacity": self.capacity,
            "percentage": int((self.current_level / self.capacity) * 100) if self.capacity > 0 else 0,
            "is_full": self.current_level >= self.capacity
        }

    def _record_event(self, event_type, previous_level, new_level, amount, source):
        """Log a state transition event into in-memory history."""
        self.history.append({
            "timestamp": time.time(),
            "event_type": event_type,
            "previous_level": previous_level,
            "new_level": new_level,
            "amount": amount,
            "source": source
        })
        # Constrain history to the last 100 events to prevent memory bloating
        if len(self.history) > 100:
            self.history.pop(0)
