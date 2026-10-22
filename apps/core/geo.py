"""Where a point on the site plan lies on the earth, for the sun and map links.

The plot map (720 × 1000, east up) was laid over Kartverket's topo map (22.10.2026): the plots'
drawn areas against their real m² give the scale, the plan's compass gives the directions, and
the roads and streams fixed the position. The plan is a simplified drawing, so a point is right
to within about 30–50 m – fine for the sun's path and a map of the field, not for boundaries.
"""
import math

METRES_PER_UNIT = 0.886      # from the 54 plots' drawn area vs. their area in m²
ANCHOR_X, ANCHOR_Y = 360.0, 500.0  # the middle of the drawing ...
ANCHOR_LAT, ANCHOR_LON = 61.0177, 8.9446  # ... lies here
METRES_PER_DEGREE_LAT = 111_195.0

SUNCALC_ZOOM = 17


def plan_to_latlon(x, y):
    """(51.4, 410.7) on the plan -> (61.02016, 8.94607). +x on the plan is south, +y is west."""
    north = -(x - ANCHOR_X) * METRES_PER_UNIT
    east = -(y - ANCHOR_Y) * METRES_PER_UNIT
    lat = ANCHOR_LAT + north / METRES_PER_DEGREE_LAT
    lon = ANCHOR_LON + east / (METRES_PER_DEGREE_LAT * math.cos(math.radians(ANCHOR_LAT)))
    return round(lat, 5), round(lon, 5)


def sun_url(lat, lon):
    """suncalc.org at the point: the sun's path through the day, sunrise and sunset, for any date."""
    return f'https://www.suncalc.org/#/{lat},{lon},{SUNCALC_ZOOM}'
