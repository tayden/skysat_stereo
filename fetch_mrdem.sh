#!/usr/bin/env bash
#
# fetch_mrdem.sh — Fetch the MRDEM-30 DTM for an AOI and prepare it for the
# SkySat stereo pipeline.
#
# Steps performed in a single gdalwarp call:
#   1. Stream only the needed window from the cloud-optimised GeoTIFF on S3
#      (via /vsicurl/ — no full download).
#   2. Convert the native CGVD2013 *orthometric* heights to WGS84 *ellipsoidal*
#      heights (PROJ applies the ca_nrc_CGG2013an83 geoid grid, ~ -14 m here),
#      so the output matches the ellipsoidal convention RPC orthorectification
#      expects (same as the existing refdem_utm10_ellip.tif).
#   3. Reproject from EPSG:3979 (Canada Atlas Lambert) to the target UTM zone
#      and crop to the AOI bounding box.
#
# Run inside the project environment:   pixi run bash fetch_mrdem.sh
#
# Any parameter below can be overridden from the environment, e.g.:
#   OUT=/tmp/dem.tif LAT_MIN=50.30 pixi run bash fetch_mrdem.sh
#
set -euo pipefail

# ---- configurable parameters --------------------------------------------
SRC="${SRC:-/vsicurl/https://canelevation-dem.s3.ca-central-1.amazonaws.com/mrdem-30/mrdem-30-dtm.tif}"
OUT="${OUT:-/home/acouser/asp/data/dems/mrdem30_utm10_ellip.tif}"
T_SRS="${T_SRS:-EPSG:32610}"          # target horizontal CRS (UTM zone 10N)
S_SRS="${S_SRS:-EPSG:3979+6647}"      # MRDEM horizontal (3979) + CGVD2013 height (6647)
TR="${TR:-30}"                        # output pixel size (m)
RESAMPLE="${RESAMPLE:-bilinear}"
SRC_NODATA="${SRC_NODATA:--32767}"    # MRDEM nodata
DST_NODATA="${DST_NODATA:--32767}"

# AOI bounding box in lon/lat (WGS84). Defaults cover the SkySat scene-footprint
# union reported by pipeline step 1 (lon -122.661..-122.564, lat 50.387..50.460)
# with a margin so every scene — including the southern ssc4d1_0016 — is fully
# on the DEM. Widen these if you add scenes outside this box.
LON_MIN="${LON_MIN:--122.70}"
LAT_MIN="${LAT_MIN:-50.36}"
LON_MAX="${LON_MAX:--122.52}"
LAT_MAX="${LAT_MAX:-50.49}"
# -------------------------------------------------------------------------

# Allow PROJ to fetch the CGVD2013 geoid grid from cdn.proj.org if it is not
# already cached locally (a one-off ~10 MB download).
export PROJ_NETWORK=ON

# Project the lon/lat AOI corners into the target CRS to get a -te extent.
read -r XMIN YMIN XMAX YMAX < <(
  python - "$T_SRS" "$LON_MIN" "$LAT_MIN" "$LON_MAX" "$LAT_MAX" <<'PY'
import sys
from pyproj import Transformer
t_srs = sys.argv[1]
lonmin, latmin, lonmax, latmax = map(float, sys.argv[2:6])
tr = Transformer.from_crs("EPSG:4326", t_srs, always_xy=True)
xs, ys = [], []
for lon in (lonmin, lonmax):
    for lat in (latmin, latmax):
        x, y = tr.transform(lon, lat)
        xs.append(x)
        ys.append(y)
print(min(xs), min(ys), max(xs), max(ys))
PY
)

echo "Source : $SRC"
echo "Output : $OUT"
echo "AOI    : lon [$LON_MIN, $LON_MAX]  lat [$LAT_MIN, $LAT_MAX]"
echo "Extent : $T_SRS  $XMIN $YMIN $XMAX $YMAX"
echo "Heights: CGVD2013 orthometric -> WGS84 ellipsoidal"
echo

mkdir -p "$(dirname "$OUT")"

gdalwarp -overwrite \
  -s_srs "$S_SRS" -t_srs "$T_SRS" \
  -te "$XMIN" "$YMIN" "$XMAX" "$YMAX" \
  -tr "$TR" "$TR" -r "$RESAMPLE" \
  -srcnodata "$SRC_NODATA" -dstnodata "$DST_NODATA" \
  -co COMPRESS=DEFLATE -co TILED=YES -co BIGTIFF=IF_SAFER \
  "$SRC" "$OUT"

echo
echo "Done. Summary:"
gdalinfo -stats "$OUT" | grep -iE "Size is|Pixel Size|STATISTICS_MINIMUM|STATISTICS_MAXIMUM|STATISTICS_MEAN"
echo
echo "To use it, point main.sh at:"
echo "  -coregdem $OUT"
echo "  -orthodem $OUT"
