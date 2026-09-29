from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from transit_audit.geo.census import load_census_geopackage, population_within_distance

FIXTURES = Path(__file__).parent / "fixtures"


def test_missing_dguid_column(tmp_path: Path) -> None:
    path = tmp_path / "bad.gpkg"
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"population": [1]}, geometry=[polygon], crs="EPSG:4326")
    gdf.to_file(path, driver="GPKG")
    with pytest.raises(ValueError, match="DGUID"):
        load_census_geopackage(path)


def test_empty_stops_returns_zero_coverage() -> None:
    census = load_census_geopackage(FIXTURES / "census_tiny.gpkg")
    empty_stops = gpd.GeoDataFrame(geometry=[], crs=census.gdf.crs)
    covered, total, meta = population_within_distance(census, empty_stops, 500)
    assert covered == 0.0
    assert total == 500.0
    assert meta["population_method"] == "areal_weight"
