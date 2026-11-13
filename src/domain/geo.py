from math import asin, cos, radians, sin, sqrt
from .models import Node

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(first: Node, second: Node) -> float:
    lat1, lat2 = radians(first.latitude), radians(second.latitude)
    delta_lat = lat2 - lat1
    delta_lon = radians(second.longitude - first.longitude)
    value = sin(delta_lat / 2)**2 + cos(lat1)*cos(lat2)*sin(delta_lon / 2)**2
    return 2 * EARTH_RADIUS_M * asin(sqrt(min(1.0, max(0.0, value))))
