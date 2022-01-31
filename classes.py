class Appliance:
    def __init__(self, power, feeder = 0):
        self.power = power
        self.feeder = feeder

class Request:
    def __init__(self, equipment, availability, required, total_time):
        self.equipment = equipment
        self.availability = availability
        self.required = required
        self.total_time = total_time

class Schedule:
    pass

class Solver:
    pass