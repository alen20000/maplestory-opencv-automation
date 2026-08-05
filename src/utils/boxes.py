from dataclasses import dataclass

@dataclass
class BBox:
    '''
    放置矩形座標
    format:x_min, y_min, x_max, y_max
    '''
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def top_left(self) -> tuple[int, int]:
        return (self.x1, self.y1)

    @property
    def bottom_right(self) -> tuple[int, int]:
        return (self.x2, self.y2)