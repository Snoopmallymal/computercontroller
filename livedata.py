import redis
import os

class LiveData:
    """
    Manages live data using Redis + file backup for minutes.
    """

    def __init__(self, id, default_minutes=10):
        # connect to Redis
        self.r = redis.Redis(host='localhost', port=6379, db=0)
        self.MINUTES_FILE = f"{id}_minutes_backup.txt"
        self.MINUTES_KEY = f"{id}:minutes_left"
        self.LOCK_KEY = f"{id}:lock_mode"

        # Initialize minutes: first try Redis, then file, else default
        if not self.r.exists(self.MINUTES_KEY):
            minutes = self.load_minutes_from_file()
            if minutes == 0:
                minutes = default_minutes
            self.r.set(self.MINUTES_KEY, minutes)
            self.save_minutes_to_file(minutes)

    def load_minutes_from_file(self):
        if os.path.exists(self.MINUTES_FILE):
            try:
                with open(self.MINUTES_FILE, "r") as f:
                    return int(f.read())
            except ValueError:
                return 0
        return 0

    def save_minutes_to_file(self, minutes):
        with open(self.MINUTES_FILE, "w") as f:
            f.write(str(minutes))

    def adjust_time(self, delta_minutes):
        current_minutes = int(self.r.get(self.MINUTES_KEY) or 0)
        new_minutes = max(0, current_minutes + delta_minutes)
        self.r.set(self.MINUTES_KEY, new_minutes)
        self.save_minutes_to_file(new_minutes)
        return new_minutes

    def get_minutes(self):
        return int(self.r.get(self.MINUTES_KEY) or 0)
    
    def get_lock_mode(self):
        val = self.r.get(self.LOCK_KEY)
        return val.decode() if val else None
    
    def set_lock_mode(self, mode):
        if mode in ["locked", "unlocked"]:
            self.r.set(self.LOCK_KEY, mode)
        else:
            raise ValueError("Invalid lock mode.")
 