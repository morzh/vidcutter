class BoundingBox:
    """
    Image bounding box in normalized coordinates
    """
    def __init__(self):
        self._x = 0.0
        self._y = 0.0
        self._width = 1.0
        self._height = 1.0
        self._confidence = 1.0

    def clamp_(self, x, min, max):
        if x < min:
            return min
        elif x > max:
            return max
        else:
            return x

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value) -> None:
        self._x = self.clamp_(value, 0, 1)

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value) -> None:
        self._y = self.clamp_(value, 0, 1)

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value) -> None:
        self._width = self.clamp_(value, 0, 1)

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value) -> None:
        self._height = self.clamp_(value, 0, 1)

    @property
    def confidence(self) -> float:
        return self._confidence

    @confidence.setter
    def confidence(self, value) -> None:
        self._confidence = self.clamp_(value, 0, 1)


ee = BoundingBox()
