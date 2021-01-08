class Simulation:
    """Main simulation class in this project"""

    interval = 1


    def __init__(self, interval, world, start=None, end=None):
        self.interval = interval

        self.world = world

        self.start = start
        self.end = end

    def run(self):
        """Runs Simulation"""
        #TODO write simulation

    def runStep(self):
        """Runs Simulation one step"""


    def __repr__(self):
        return "sailsim\n@%sHz, frame %s/%s\n%s" % (1/self.interval, self.frame, self.maxFrames, self.world.__str()__)
