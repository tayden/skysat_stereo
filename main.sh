skysat_triplet_pipeline.py \
  -in_img      /home/acouser/asp/data/Place_Skysat_Scenes_ACOAOI_20260612_skysatscene_basic_panchromatic/SkySatScene/ \
  -coregdem    /home/acouser/asp/data/dems/mrdem30_utm10_ellip.tif \
  -orthodem    /home/acouser/asp/data/dems/mrdem30_utm10_ellip.tif \
  -aoi_bbox    /home/acouser/asp/data/geom/aoi/4012_PlaceGlacier_AOI.shp \
  -ortho_workflow 1 \
  -mask_dem    1 \
  -mask_dem_opt glaciers \
  -job_name    place_glacier_site1 \
  -outfolder   /home/acouser/asp/data/output
