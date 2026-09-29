"""Census geography loading and distance projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely.geometry import Point

PopulationMethod = Literal["areal_weight", "population_points"]


@dataclass
class CensusLayer:
    gdf: gpd.GeoDataFrame
    epsg: int
    population_column: str = "population"
    source_crs: str | None = None
    population_method: PopulationMethod = "areal_weight"


def project_for_distance(
    gdf: gpd.GeoDataFrame,
    target_epsg: int = 3347,
    source_crs: str | None = None,
) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        if source_crs is None:
            raise ValueError(
                "Census layer has no CRS. Set CRS on the file or provide "
                "census_crs in the audit config."
            )
        gdf = gdf.set_crs(source_crs)
    return gdf.to_crs(epsg=target_epsg)


def load_census_geopackage(
    path: Path,
    target_epsg: int = 3347,
    census_crs: str | None = None,
    population_method: PopulationMethod = "areal_weight",
) -> CensusLayer:
    gdf = gpd.read_file(path)
    if "DGUID" not in gdf.columns:
        raise ValueError("Census layer must include a DGUID column")
    if "population" not in gdf.columns:
        raise ValueError("Census layer must include a population column")

    source_crs = str(gdf.crs) if gdf.crs is not None else census_crs
    projected = project_for_distance(gdf, target_epsg=target_epsg, source_crs=census_crs)
    return CensusLayer(
        gdf=projected,
        epsg=target_epsg,
        source_crs=source_crs,
        population_method=population_method,
    )


def stops_to_gdf(
    stops: pd.DataFrame,
    target_epsg: int,
) -> gpd.GeoDataFrame:
    if stops.empty:
        return gpd.GeoDataFrame(geometry=[], crs=CRS.from_epsg(4326)).to_crs(epsg=target_epsg)

    frame = stops.copy()
    frame["stop_lon"] = pd.to_numeric(frame["stop_lon"], errors="coerce")
    frame["stop_lat"] = pd.to_numeric(frame["stop_lat"], errors="coerce")
    valid = frame[
        frame["stop_lon"].notna()
        & frame["stop_lat"].notna()
        & frame["stop_lon"].between(-180, 180)
        & frame["stop_lat"].between(-90, 90)
    ].copy()

    geometry = [
        Point(
            float(cast(Any, valid.at[idx, "stop_lon"])),
            float(cast(Any, valid.at[idx, "stop_lat"])),
        )
        for idx in valid.index
    ]
    gdf = gpd.GeoDataFrame(valid, geometry=geometry, crs=CRS.from_epsg(4326))
    return gdf.to_crs(epsg=target_epsg)


def _areal_weighted_population(
    census_gdf: gpd.GeoDataFrame,
    buffers: object,
    population_column: str,
) -> float:
    covered = 0.0
    for _, row in census_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        poly_area = geom.area
        if poly_area <= 0:
            continue
        intersection = geom.intersection(buffers)
        if intersection.is_empty:
            continue
        weight = intersection.area / poly_area
        covered += float(cast(Any, row[population_column])) * weight
    return covered


def population_within_distance(
    census: CensusLayer,
    stops_gdf: gpd.GeoDataFrame,
    threshold_m: float,
) -> tuple[float, float, dict[str, object]]:
    total_pop = float(
        cast(float, census.gdf[census.population_column].astype(float).sum())
    )
    metadata: dict[str, object] = {
        "population_method": census.population_method,
        "crs_epsg": census.epsg,
        "source_crs": census.source_crs,
        "target_crs": f"EPSG:{census.epsg}",
        "assumption": "uniform_population_density_within_polygon",
        "limit": "Descriptive proximity association; not walk accessibility or legal compliance.",
    }

    if stops_gdf.empty:
        return 0.0, total_pop, metadata

    buffers = stops_gdf.geometry.buffer(threshold_m).union_all()

    if census.population_method == "areal_weight":
        covered = _areal_weighted_population(census.gdf, buffers, census.population_column)
        metadata["weighting"] = "intersection_area_over_polygon_area"
    else:
        touched = census.gdf[census.gdf.intersects(buffers)]
        covered = float(
            cast(float, touched[census.population_column].astype(float).sum())
        )
        metadata["weighting"] = "binary_intersection_full_polygon_count"

    return covered, total_pop, metadata
