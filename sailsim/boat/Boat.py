from math import sin, sqrt, pi

from sailsim.utils.constants import DENSITY_AIR, DENSITY_WATER
from sailsim.utils.coordconversion import cartToArg

from sailsim.boat.BoatDataHolder import BoatDataHolder


class Boat:
    """Holds all information about the boat and calculates its speed, forces and torques."""

    def __init__(self, posX, posY, mass, area, sailor):
        # Static properties
        self.mass = mass
        self.sailArea = area
        self.hullArea = 4 # arbitrary
        self.centerboardArea = 1

        self.FORCE_CONST_AIR = 0.5 * DENSITY_AIR * self.sailArea # kg / m
        # self.FORCE_CONST_AIR_LIFT = 0.5 * DENSITY_AIR * self.sailArea
        self.FORCE_CONST_WATER = 0.5 * DENSITY_WATER * (self.hullArea + self.centerboardArea) # kg / m
        self.FORCE_CONST_WATER_LIFT = 0.5 * DENSITY_WATER * self.centerboardArea

        # Dynamic properties
        self.posX = posX
        self.posY = posY

        self.speedX = 0
        self.speedY = 0
        self.leewayAngle = 0

        self.sailor = sailor # Sail algorithm
        self.mainSailAngle = 45 * pi / 180

        self.dataHolder = BoatDataHolder()


    # Simulation
    def applyForce(self, forceX, forceY, interval):
        """Change speed according a force given."""
        # △v = a * t ; F = m * a
        # △v = F / m * t
        self.speedX += forceX / self.mass * interval
        self.speedY += forceY / self.mass * interval

    def moveInterval(self, interval):
        """Change position according to sailsDirection and speed."""
        # s = v * t
        self.posX += self.speedX * interval
        self.posY += self.speedY * interval

    def runSailor(self):
        """Activate the sailing algorithm to decide what the boat should do."""
        # TODO interact with sailor library

    # Force calculations
    def resultingForce(self, trueWindX, trueWindY):
        """Add up all reacting forces and return them as a tuple."""
        h = self.dataHolder

        # calculate apparent wind angle
        (h.apparentWindX, h.apparentWindY) = self.apparentWind(trueWindX, trueWindY)
        h.apparentWindAngle = self.apparentWindAngle(h.apparentWindX, h.apparentWindY)

        apparentWindSpeedSq = self.apparentWindSpeedSq(h.apparentWindX, h.apparentWindY)
        h.apparentWindSpeed = sqrt(apparentWindSpeedSq)
        boatSpeedSq = self.boatSpeedSq()
        h.boatSpeed = sqrt(boatSpeedSq)

        # normalise apparent wind vector and boat speed vetor
        # if vector is (0, 0) set normalised vector to (0, 0) aswell
        (apparentWindNormX, apparentWindNormY) = (h.apparentWindX / h.apparentWindSpeed, h.apparentWindY / h.apparentWindSpeed) if not h.apparentWindSpeed == 0 else (0, 0) # normalised apparent wind vector
        (speedNormX, speedNormY) = (self.speedX / h.boatSpeed, self.speedY / h.boatSpeed) if not h.boatSpeed == 0 else (0, 0) # normalised speed vector

        h.leewayAngle = self.calcLeewayAngle()
        h.angleOfAttack = self.angleOfAttack(h.apparentWindAngle)

        # print("apWind:", h.apparentWindX, h.apparentWindY)
        # print("apWindAng:", h.apparentWindAngle * 180 / pi)
        # print("angOfAtk:", h.angleOfAttack * 180 / pi)

        # Sum up all acting forces
        # FIXME check if this can be implemented nicer
        forceX, forceY = 0, 0
        (h.sailDragX, h.sailDragY) = self.sailDrag(apparentWindNormX, apparentWindNormY, apparentWindSpeedSq)
        forceX += h.sailDragX
        forceY += h.sailDragY
        (h.sailLiftX, h.sailLiftY) = self.sailLift(apparentWindNormX, apparentWindNormY, apparentWindSpeedSq)
        forceX += h.sailLiftX
        forceY += h.sailLiftY

        (h.waterDragX, h.waterDragY) = self.waterDrag(speedNormX, speedNormY, boatSpeedSq)
        forceX += h.waterDragX
        forceY += h.waterDragY
        (h.waterLiftX, h.waterLiftY) = self.waterLift(speedNormX, speedNormY, boatSpeedSq)
        forceX += h.waterLiftX
        forceY += h.waterLiftY

        # print(self.speedX, self.speedY)
        # print(h.sailDragX, h.sailDragY)
        # print(h.sailLiftX, h.sailLiftY)
        # print(h.waterDragX, h.waterDragY)
        # print(h.waterLiftX, h.waterLiftY)
        # print(forceX, forceY)
        # print("----------")

        (h.forceX, h.forceY) = (forceX, forceY)
        return (forceX, forceY)

    def sailDrag(self, apparentWindNormX, apparentWindNormY, apparentWindSpeedSq):
        """Calculate the force that is created when wind blows against the boat."""
        force = self.FORCE_CONST_AIR * apparentWindSpeedSq * sin(self.dataHolder.angleOfAttack) * self.coefficientAirDrag(self.dataHolder.angleOfAttack)
        return (force * apparentWindNormX, force * apparentWindNormY)

    def sailLift(self, apparentWindNormX, apparentWindNormY, apparentWindSpeedSq):
        """Calculate the lift force that is created when the wind changes its direction in the sail."""
        force = self.FORCE_CONST_AIR * apparentWindSpeedSq * sin(self.dataHolder.angleOfAttack) * self.coefficientAirLift(self.dataHolder.angleOfAttack)
        if self.dataHolder.apparentWindAngle > 0: # NOTE potential error
            return (-force * apparentWindNormY, force * apparentWindNormX)  # rotate by -90°
        return (force * apparentWindNormY, -force * apparentWindNormX)      # rotate by  90°

    def waterDrag(self, speedNormX, speedNormY, boatSpeedSq):
        """Calculate the drag force of the water that is decelerating the boat."""
        force = self.FORCE_CONST_WATER * boatSpeedSq * sin(self.dataHolder.leewayAngle) * self.coefficientWaterDrag(self.dataHolder.leewayAngle)
        return (-force * speedNormX, -force * speedNormY) # TODO waterDrag

    def waterLift(self, speedNormX, speedNormY, boatSpeedSq):
        """Calculate force that is caused by lift forces in the water."""
        force = self.FORCE_CONST_WATER_LIFT * boatSpeedSq * sin(self.dataHolder.leewayAngle) * self.coefficientWaterLift(self.dataHolder.leewayAngle)
        if self.dataHolder.apparentWindAngle > 0: # NOTE potential error
            return (-force * speedNormY, force * speedNormX)    # rotate by  90°
        return (force * speedNormY, -force * speedNormX)        # rotate by -90°


    # Coefficient calculations
    def coefficientAirDrag(self, angleOfAttack):
        """Calculate the wind resitance coefficient based on the angle of attack."""
        # NOTE function has been approximated!
        # TODO calculate coefficient using Xfoil
        return 0.41 * pow(angleOfAttack, 2) + 0.13 * abs(angleOfAttack) + 0.3

    def coefficientAirLift(self, angleOfAttack):
        """Calculate the wind lift coefficient based on the angle of attack."""
        # NOTE function has been approximated!
        # TODO calculate coefficient using Xfoil
        if abs(angleOfAttack) > 1.07:
            return 1.67
        return 11 * pow(angleOfAttack, 4) - 22.46 * pow(abs(angleOfAttack), 3) + 7.39 * pow(angleOfAttack, 2) + 5.88 * abs(angleOfAttack)

    def coefficientWaterDrag(self, angleOfAttack):
        """Calculate the water drag coefficient based on the angle of attack."""
        # NOTE function has been approximated!
        # TODO calculate coefficient using Xfoil
        return self.coefficientAirDrag(angleOfAttack)

    def coefficientWaterLift(self, angleOfAttack):
        """Calculate the water lift coefficient based on the angle of attack."""
        # NOTE function has been approximated!
        # TODO calculate coefficient using Xfoil
        return self.coefficientAirLift(angleOfAttack)


    # Speed calculations
    def boatSpeedSq(self):
        """Return speed of the boat but squared."""
        return pow(self.speedX, 2) + pow(self.speedY, 2)

    def apparentWindSpeedSq(self, apparentWindX, apparentWindY):
        """Calculate speed of apparent wind but squared."""
        return pow(apparentWindX, 2) + pow(apparentWindY, 2) # TODO stay in (-pi;pi] => %(2*pi)


    # Angle calculations
    def calcLeewayAngle(self):
        """Calculate and return the leeway angle."""
        # TODO exact calculation
        return 3 * pi / 180

    def apparentWind(self, trueWindX, trueWindY):
        """Return apparent wind by adding true wind and speed."""
        return (trueWindX - self.speedX, trueWindY - self.speedY) # TODO stay in (-pi;pi] => %(2*pi)

    def apparentWindAngle(self, apparentWindX, apparentWindY):
        """Calculate the apparent wind angle based on the carthesian true wind."""
        angle = cartToArg(apparentWindX, apparentWindY) - cartToArg(self.speedX, self.speedY)
        if angle > pi:
            return angle - 2 * pi
        return angle # TODO stay in (-pi;pi] => %(2*pi)

    def angleOfAttack(self, apparentWindAngle): # TODO angleOfAttack oder vielleicht Segeleinstellung? Zusammenhang mit apparentWindAngle und Abdrift?
        """Calculate angle between main sail and apparent wind vector."""
        angle = pi - apparentWindAngle - self.mainSailAngle - self.leewayAngle
        if angle > pi:
            return angle - 2 * pi
        return angle # TODO stay in (-pi;pi] => %(2*pi)


    def __repr__(self):
        heading = round(cartToArg(self.speedX, self.speedY) * 180 / pi, 2)
        return "Boat @(%s|%s), v=%sm/s twds %s°" % (round(self.posX, 3), round(self.posY, 3), round(sqrt(self.boatSpeedSq()), 2), heading)
