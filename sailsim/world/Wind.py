from sailsim.utils.coordconversion import cartToPolar


class Wind:
    """This class holds all windfields and calculates speed and direction of wind."""

    def __init__(self, winds):
        self.winds = winds

    def getWindCart(self, x, y, t):
        """Summ up and returns the speed and direction of all windfields."""
        sumX = 0
        sumY = 0
        for wind in self.winds:
            (windX, windY) = wind.getWindCart(x, y, t)
            sumX += windX
            sumY += windY
        return (sumX, sumY)

    def getWind(self, x, y, t):
        """Return direction and speed of the windfield at the position (x,y) as a tuple."""
        (cartX, cartY) = self.getWindCart(x, y, t)
        return cartToPolar(cartX, cartY)
