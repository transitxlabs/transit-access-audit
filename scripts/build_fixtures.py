#!/usr/bin/env python3
"""Build synthetic GTFS and census fixtures for tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _write_zip(name: str, files: dict[str, str]) -> None:
    path = FIXTURES / name
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)


def build_fixtures() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)

    common_calendar = (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "WEEKDAY,1,1,1,1,1,0,0,20240101,20241231\n"
    )
    common_routes = (
        "route_id,agency_id,route_short_name,route_type\n"
        "R1,A1,1,3\n"
        "R2,A1,2,3\n"
    )
    common_stops = (
        "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type\n"
        "S1,Stop One,48.4284,-123.3656,1,0\n"
        "S2,Stop Two,48.4290,-123.3640,1,0\n"
        "S3,Stop Three,48.4300,-123.3630,1,0\n"
        "S4,Stop Four,48.4310,-123.3620,1,0\n"
        "S5,Stop Five,48.4320,-123.3610,1,0\n"
        "STN1,Station Alpha,48.4330,-123.3600,1,1\n"
    )
    common_trips = (
        "route_id,service_id,trip_id,trip_headsign,wheelchair_accessible\n"
        "R1,WEEKDAY,T1,East,1\n"
        "R2,WEEKDAY,T2,West,1\n"
    )
    common_stop_times = (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
        "T1,07:00:00,07:00:00,S1,1\n"
        "T1,07:15:00,07:15:00,S2,2\n"
        "T1,07:30:00,07:30:00,S3,3\n"
        "T1,08:00:00,08:00:00,S4,4\n"
        "T2,07:10:00,07:10:00,S5,1\n"
        "T2,07:40:00,07:40:00,S1,2\n"
    )

    _write_zip(
        "minimal_valid.zip",
        {
            "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nA1,Test Agency,https://example.com,America/Vancouver\n",
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
            "feed_info.txt": "feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date\nTest,https://example.com,en,20240101,20241231\n",
        },
    )

    missing_wheelchair_stops = (
        "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type\n"
        "S1,Stop One,48.4284,-123.3656,,0\n"
        "S2,Stop Two,48.4290,-123.3640,,0\n"
        "S3,Stop Three,48.4300,-123.3630,,0\n"
        "S4,Stop Four,48.4310,-123.3620,,0\n"
        "S5,Stop Five,48.4320,-123.3610,,0\n"
        "STN1,Station Alpha,48.4330,-123.3600,,1\n"
    )
    _write_zip(
        "missing_wheelchair.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": missing_wheelchair_stops,
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
        },
    )

    conflict_trips = common_trips.replace("T1,East,1", "T1,East,1").replace(
        "T2,West,1", "T2,West,1"
    )
    conflict_stops = common_stops.replace("S1,Stop One,48.4284,-123.3656,1,0", "S1,Stop One,48.4284,-123.3656,0,0")
    _write_zip(
        "trip_stop_conflict.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": conflict_stops,
            "trips.txt": conflict_trips,
            "stop_times.txt": common_stop_times,
        },
    )

    _write_zip(
        "broken_references.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": "route_id,service_id,trip_id\nR99,WEEKDAY,T9\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT9,07:00:00,07:00:00,S1,1\n",
        },
    )

    _write_zip(
        "pathways.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
            "pathways.txt": "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional,length,traversal_time\nP1,STN1,S1,1,1,10,30\n",
        },
    )

    flex_routes = (
        "route_id,agency_id,route_short_name,route_type\n"
        "FR1,A1,Flex,3\n"
    )
    _write_zip(
        "flex_service.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": flex_routes,
            "stops.txt": common_stops,
            "trips.txt": "route_id,service_id,trip_id\nFR1,WEEKDAY,FT1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nFT1,07:00:00,07:00:00,S1,1\n",
            "booking_rules.txt": "booking_rule_id,booking_type,pickup_message\nBR1,0,Call ahead\n",
            "locations.geojson": json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [
                                        [-123.37, 48.42],
                                        [-123.36, 48.42],
                                        [-123.36, 48.44],
                                        [-123.37, 48.44],
                                        [-123.37, 48.42],
                                    ]
                                ],
                            },
                            "properties": {"location_id": "Z1"},
                        }
                    ],
                }
            ),
        },
    )

    invalid_flex = _read_zip_dict("flex_service.zip")
    invalid_flex["locations.geojson"] = '{"type":"NotAFeatureCollection"}'
    _write_zip("flex_invalid_geometry.zip", invalid_flex)

    polygons = [
        Polygon([(-123.37, 48.42), (-123.36, 48.42), (-123.36, 48.44), (-123.37, 48.44)]),
        Polygon([(-123.35, 48.42), (-123.34, 48.42), (-123.34, 48.44), (-123.35, 48.44)]),
        Polygon([(-123.39, 48.40), (-123.38, 48.40), (-123.38, 48.41), (-123.39, 48.41)]),
        Polygon([(-123.33, 48.40), (-123.32, 48.40), (-123.32, 48.41), (-123.33, 48.41)]),
    ]
    gdf = gpd.GeoDataFrame(
        {
            "DGUID": ["20210010001", "20210010002", "20210010003", "20210010004"],
            "population": [100, 200, 50, 150],
            "group_code": ["ref", "low", "ref", "low"],
        },
        geometry=polygons,
        crs="EPSG:4326",
    )
    gdf.to_file(FIXTURES / "census_tiny.gpkg", driver="GPKG")

    no_crs_gdf = gpd.GeoDataFrame(
        {
            "DGUID": ["20210010005"],
            "population": [100],
            "group_code": ["ref"],
        },
        geometry=[Polygon([(-123.37, 48.42), (-123.36, 48.42), (-123.36, 48.44), (-123.37, 48.44)])],
    )
    no_crs_gdf.to_file(FIXTURES / "census_no_crs.gpkg", driver="GPKG")

    agency_line = (
        "agency_id,agency_name,agency_url,agency_timezone\n"
        "A1,Test Agency,https://example.com,America/Vancouver\n"
    )

    _write_zip(
        "calendar_exception.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": (
                "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                "WEEKDAY,1,1,1,1,1,0,0,20240101,20241231\n"
                "SATURDAY,0,0,0,0,0,1,0,20240101,20241231\n"
            ),
            "calendar_dates.txt": (
                "service_id,date,exception_type\n"
                "SATURDAY,20240603,1\n"
                "WEEKDAY,20240603,2\n"
            ),
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": (
                "route_id,service_id,trip_id,trip_headsign,wheelchair_accessible\n"
                "R1,WEEKDAY,T1,East,1\n"
                "R1,SATURDAY,T3,Saturday,1\n"
            ),
            "stop_times.txt": (
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "T1,07:00:00,07:00:00,S1,1\n"
                "T3,10:00:00,10:00:00,S1,1\n"
            ),
        },
    )

    _write_zip(
        "frequencies.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": "route_id,service_id,trip_id,trip_headsign,wheelchair_accessible\nR1,WEEKDAY,T1,East,1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,07:00:00,07:00:00,S1,1\n",
            "frequencies.txt": (
                "trip_id,start_time,end_time,headway_secs,exact_times\n"
                "T1,07:00:00,08:00:00,900,0\n"
            ),
        },
    )

    _write_zip(
        "wheelchair_inheritance.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type,parent_station\n"
                "STN1,Station,48.4330,-123.3600,1,1,\n"
                "PLAT1,Platform,48.4331,-123.3601,,0,STN1\n"
                "PLAT2,Platform Two,48.4332,-123.3602,0,0,STN1\n"
            ),
            "trips.txt": common_trips,
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,07:00:00,07:00:00,PLAT1,1\n",
        },
    )

    _write_zip(
        "malformed_coords.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type\n"
                "S1,Bad,not-a-lat,not-a-lon,1,0\n"
                "S2,Far,91.0,0.0,1,0\n"
                "S3,Ok,48.4284,-123.3656,1,0\n"
            ),
            "trips.txt": common_trips,
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,07:00:00,07:00:00,S3,1\n",
        },
    )

    _write_zip(
        "directed_pathways.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type,parent_station\n"
                "STN1,Station,48.4330,-123.3600,1,1,\n"
                "ENT1,Entrance,48.4331,-123.3601,1,2,STN1\n"
                "PLAT1,Platform,48.4332,-123.3602,1,0,STN1\n"
                "BAD1,Bad From,48.4340,-123.3610,1,0,\n"
                "BAD2,Bad To,48.4341,-123.3611,1,0,\n"
            ),
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
            "pathways.txt": (
                "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional,length,traversal_time\n"
                "P1,ENT1,PLAT1,1,0,10,30\n"
                "P2,BAD1,BAD2,9,1,5,10\n"
            ),
        },
    )

    _write_zip(
        "missing_agency.zip",
        {
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
        },
    )

    _write_zip(
        "missing_calendar.zip",
        {
            "agency.txt": agency_line,
            "routes.txt": common_routes,
            "stops.txt": common_stops,
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
        },
    )

    _write_zip(
        "unreachable_platform.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding,location_type,parent_station\n"
                "STN1,Station,48.4330,-123.3600,1,1,\n"
                "ENT1,Entrance,48.4331,-123.3601,1,2,STN1\n"
                "PLAT1,Platform,48.4332,-123.3602,1,0,STN1\n"
            ),
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
            "pathways.txt": (
                "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional,length,traversal_time\n"
                "P1,ENT1,STN1,1,0,10,30\n"
            ),
        },
    )

    _write_zip(
        "no_location_type.zip",
        {
            "agency.txt": agency_line,
            "calendar.txt": common_calendar,
            "routes.txt": common_routes,
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon,wheelchair_boarding\n"
                "S1,Stop One,48.4284,-123.3656,1\n"
                "STN1,Station Alpha,48.4330,-123.3600,1\n"
            ),
            "trips.txt": common_trips,
            "stop_times.txt": common_stop_times,
        },
    )


def _read_zip_dict(name: str) -> dict[str, str]:
    files: dict[str, str] = {}
    with zipfile.ZipFile(FIXTURES / name) as archive:
        for member in archive.namelist():
            files[member] = archive.read(member).decode("utf-8")
    return files


if __name__ == "__main__":
    build_fixtures()
