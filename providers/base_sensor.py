from abc import ABC, abstractmethod

class BaseSensorProvider(ABC):
    @abstractmethod
    def read_distance(self):
        """Returns the current raw distance measurement in cm from the top sensor to the water surface."""
        pass

    @abstractmethod
    def get_status(self):
        """Returns the hardware/connection status of the sensor provider."""
        pass
