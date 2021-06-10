from math import sqrt, pi, sin, cos

from sailsim.utils.anglecalculations import angleKeepInterval, directionKeepInterval
from sailsim.utils.coordconversion import cartToRadiusSq, cartToArg

from sailsim.boat.BoatDataHolder import BoatDataHolder
from sailsim.boat.coefficientsapprox import coefficientAirDrag, coefficientAirLift, coefficientWaterDrag, coefficientWaterLift


class Boat:
    """Holds all information about the boat and calculates its speed, forces and torques."""

    from .boatgetset import getPos, getSpeed, setDirection, setDirectionDeg, setMainSailAngle, setMainSailAngleDeg, setConstants

    def __init__(self, posX=0, posY=0, direction=0, speedX=0, speedY=0, angSpeed=0):
        """
        Create a boat.

        Args:
            posX:       x position of the boat (in m)
            posY:       y position of the boat (in m)
            direction:  direction the boat is pointing (in rad)
            speedX:     speed in x direction (in m/s)
            speedY:     speed in y direction (in m/s)
            angSpeed:   angular speed in z direction (in rad/s)
        """
        # Dynamic properties
        self.posX = posX
        self.posY = posY
        self.speedX = speedX
        self.speedY = speedY

        self.direction = directionKeepInterval(direction)
        self.angSpeed = angSpeed    # rad/s

        self.mainSailAngle = 0
        self.maxMainSailAngle = 80 / 180 * pi

        self.rudderAngle = 0
        self.maxRudderAngle = 80 / 180 * pi

        self.dataHolder = BoatDataHolder()
        self.sailor = None

        # Static properties
        self.length = 4.2           # m
        self.width = 1.63           # m
        self.mass = 80              # kg
        self.momentumInertia = 1/12 * self.mass * (pow(self.length, 2) + pow(self.width, 2))  # kg/m^2
        self.sailArea = 7.45        # m^2
        self.hullArea = 4           # m^2
        self.centerboardArea = 1    # m^2
        self.rudderArea = .175      # m^2

        # Coefficients methods
        self.coefficientAirDrag = coefficientAirDrag
        self.coefficientAirLift = coefficientAirLift
        self.coefficientWaterDrag = coefficientWaterDrag
        self.coefficientWaterLift = coefficientWaterLift

        self.tackingAngleUpwind = 45 / 180 * pi
        self.tackingAngleDownwind = 20 / 180 * pi


    # Simulation
    def applyForce(self, forceX, forceY, interval):
        """Change speed according a force given."""
        # △v = a * t ; F = m * a
        # △v = F / m * t
        self.speedX += forceX / self.mass * interval
        self.speedY += forceY / self.mass * interval

    def applyMomentum(self, momentum, interval):
        """Change angular speed according to a momentum given."""
        # NOTE copied from applyForce()
        # FIXME move this into applyForce()? Rename applyForce() function?
        # △ω = α * t; M = I * α
        # △ω = M / I * t
        self.angSpeed += momentum / self.momentumInertia * interval

    def moveInterval(self, interval):
        """Change position according to sailsDirection and speed."""
        # s = v * t
        self.posX += self.speedX * interval
        self.posY += self.speedY * interval
        self.direction = directionKeepInterval(self.direction + self.angSpeed * interval)

    def runSailor(self):
        """Activate the sailing algorithm to decide what the boat should do."""
        self.sailor.run(
            self.posX,
            self.posY,
            self.dataHolder.boatSpeed,
            cartToArg(self.speedX, self.speedY),
            self.direction,
            self.dataHolder.apparentWindSpeed,
            self.dataHolder.apparentWindAngle
        ) # Run sailor

        # Set boat properties
        self.mainSailAngle = self.sailor.mainSailAngle
        # self.direction = self.sailor.boatDirection
        self.rudderAngle = self.sailor.rudderAngle


    # Force calculations
    def resultingForce(self, trueWindX, trueWindY):
        """Add up all acting forces and return them as a tuple."""
        h = self.dataHolder

        # calculate apparent wind angle
        (h.apparentWindX, h.apparentWindY) = self.apparentWind(trueWindX, trueWindY)
        h.apparentWindAngle = self.apparentWindAngle(h.apparentWindX, h.apparentWindY)

        apparentWindSpeedSq = cartToRadiusSq(h.apparentWindX, h.apparentWindY)
        h.apparentWindSpeed = sqrt(apparentWindSpeedSq)
        boatSpeedSq = self.boatSpeedSq()
        h.boatSpeed = sqrt(boatSpeedSq)

        # normalise apparent wind vector and boat speed vetor
        # if vector is (0, 0) set normalised vector to (0, 0) aswell
        (apparentWindNormX, apparentWindNormY) = (h.apparentWindX / h.apparentWindSpeed, h.apparentWindY / h.apparentWindSpeed) if not h.apparentWindSpeed == 0 else (0, 0) # normalised apparent wind vector
        (speedNormX, speedNormY) = (self.speedX / h.boatSpeed, self.speedY / h.boatSpeed) if not h.boatSpeed == 0 else (0, 0) # normalised speed vector
        (dirNormX, dirNormY) = (sin(self.direction), cos(self.direction))

        h.leewayAngle = self.calcLeewayAngle()
        h.angleOfAttack = self.angleOfAttack(h.apparentWindAngle)

        # Sum up all acting forces
        (forceX, forceY) = (0, 0)

        # Sail forces
        scalarSailDrag = self.sailDrag(apparentWindSpeedSq)
        (h.sailDragX, h.sailDragY) = self.scalarToDragForce(scalarSailDrag, apparentWindNormX, apparentWindNormY)
        forceX += h.sailDragX
        forceY += h.sailDragY
        scalarSailLift = self.sailLift(apparentWindSpeedSq)
        (h.sailLiftX, h.sailLiftY) = self.scalarToLiftForce(scalarSailLift, h.angleOfAttack, apparentWindNormX, apparentWindNormY)
        forceX += h.sailLiftX
        forceY += h.sailLiftY

        # Hull forces
        scalarHullDrag = self.waterDrag(boatSpeedSq)
        (h.waterDragX, h.waterDragY) = self.scalarToDragForce(scalarHullDrag, speedNormX, speedNormY)
        forceX += h.waterDragX
        forceY += h.waterDragY
        scalarHullLift = self.waterLift(boatSpeedSq)
        (h.waterLiftX, h.waterLiftY) = self.scalarToLiftForce(scalarHullLift, h.leewayAngle, speedNormX, speedNormY)
        forceX += h.waterLiftX
        forceY += h.waterLiftY

        # Rudder forces
        scalarRudderDrag = self.waterDragRudder(boatSpeedSq)
        (h.waterDragRudderX, h.waterDragRudderY) = self.scalarToDragForce(scalarRudderDrag, speedNormX, speedNormY)
        forceX += h.waterDragRudderX
        forceY += h.waterDragRudderY
        scalarRudderLift = self.waterLiftRudder(boatSpeedSq)
        print(scalarRudderLift)
        (h.waterLiftRudderX, h.waterLiftRudderY) = self.scalarToLiftForce(scalarRudderLift, angleKeepInterval(h.leewayAngle+self.rudderAngle), speedNormX, speedNormY)
        forceX += h.waterLiftRudderX
        forceY += h.waterLiftRudderY

        (h.forceX, h.forceY) = (forceX, forceY)
        return (forceX, forceY)

    from .boat_forces import sailDrag, sailLift, waterDrag, waterLift, waterDragRudder, waterLiftRudder, waterDragRudder, waterLiftRudder, scalarToDragForce, scalarToLiftForce


    # Momentum calculations
    def resultingMomentum(self):
        """Sum all acting momenta."""
        h = self.dataHolder
        resMomentum = 0

        h.waterDragMomentum = self.waterDragMomentum()
        resMomentum += h.waterDragMomentum

        h.rudderMomentum = self.rudderMomentum(self.boatSpeedSq())
        resMomentum += h.rudderMomentum

        h.momentum = resMomentum
        return resMomentum

    from .boat_momenta import waterDragMomentum, rudderMomentum


    # Speed calculations
    def boatSpeedSq(self):
        """Return speed of the boat but squared."""
        return pow(self.speedX, 2) + pow(self.speedY, 2)

    def boatSpeed(self):
        """Return speed of the boat."""
        return sqrt(pow(self.speedX, 2) + pow(self.speedY, 2))


    # Angle calculations
    def calcLeewayAngle(self):
        """Calculate and return the leeway angle."""
        return angleKeepInterval(cartToArg(self.speedX, self.speedY) - self.direction)

    def apparentWind(self, trueWindX, trueWindY):
        """Return apparent wind by adding true wind and speed."""
        return (trueWindX - self.speedX, trueWindY - self.speedY)

    def apparentWindAngle(self, apparentWindX, apparentWindY):
        """Calculate the apparent wind angle based on the carthesian true wind."""
        return angleKeepInterval(cartToArg(apparentWindX, apparentWindY) - self.direction)

    def angleOfAttack(self, apparentWindAngle):
        """Calculate angle between main sail and apparent wind vector."""
        return angleKeepInterval(apparentWindAngle - self.mainSailAngle + pi)


    def __repr__(self):
        heading = round(cartToArg(self.speedX, self.speedY) * 180 / pi, 2)
        return "Boat @(%s|%s), v=%sm/s twds %s°" % (round(self.posX, 3), round(self.posY, 3), round(sqrt(self.boatSpeedSq()), 2), heading)
