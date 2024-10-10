import os
import zipfile
import rioxarray
import numpy as np
import rasterio
from rasterio.control import GroundControlPoint
import shutil

# Paths
sentinel3_zips = '/Users/katerinaargyriparoni/data/Madrid/2021'
extracted_sentinel3 = '/Users/katerinaargyriparoni/data/Madrid/LST_2021'

# Unzip
for file_name in os.listdir(sentinel3_zips):
    if file_name.endswith('.zip'):
        zip_file_path = os.path.join(sentinel3_zips, file_name)

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            print(f"Extracting {file_name}...")
            zip_ref.extractall(extracted_sentinel3)

print("Unzipping completed successfully!")

# NetCDF
def process_nc_files(nc_data_folder, folder_name):
    try:
        # Open data from NetCDF
        with rioxarray.open_rasterio(f'netcdf:{nc_data_folder}/geodetic_in.nc:latitude_in') as lat:
            with rioxarray.open_rasterio(f'netcdf:{nc_data_folder}/geodetic_in.nc:longitude_in') as lon:
                with rioxarray.open_rasterio(f'netcdf:{nc_data_folder}/geodetic_in.nc:elevation_in') as alt:
                    with rioxarray.open_rasterio(f'netcdf:{nc_data_folder}/LST_in.nc:LST') as lst:
                        nof_gcp_x = np.arange(0, lst.x.size, 30)
                        nof_gcp_y = np.arange(0, lst.y.size, 30)
                        gcps = []
                        gcp_id = 0

                        # Create Ground Control Points
                        for x in nof_gcp_x:
                            for y in nof_gcp_y:
                                gcps.append(GroundControlPoint(row=y, col=x,
                                                               x=lon.data[0, y, x] * lon.scale_factor,
                                                               y=lat.data[0, y, x] * lat.scale_factor,
                                                               z=alt.data[0, y, x] * alt.scale_factor,
                                                               id=gcp_id))
                                gcp_id += 1

                        # Transformation from GCPs
                        tr_gcp = rasterio.transform.from_gcps(gcps)

        # Convert LST to TIFF
        def convert_to_tif(layer_name, title, folder_id):
            with rioxarray.open_rasterio(f'netcdf:{nc_data_folder}/{layer_name}') as data:
                data.rio.write_crs("EPSG:4326", inplace=True)
                data.rio.write_transform(transform=tr_gcp, inplace=True)
                filename = layer_name.split(':')[1]

                # Save TIFF
                full_title = f"{title}_{folder_id}_{filename}_reproj"
                data_final = data.rio.reproject(dst_crs="EPSG:4326", gcps=gcps, **{"SRC_METHOD": "GCP_TPS"})
                data_final.rio.to_raster(f"{nc_data_folder}/{full_title}.tif", recalc_transform=False)
                print(f'Saved {layer_name} as {full_title}.tif')


        convert_to_tif('LST_in.nc:LST', title='Sentinel-3_L2', folder_id=folder_name)

    except Exception as e:
        print(f"An error occurred: {e}")


for root, dirs, files in os.walk(extracted_sentinel3):
    for folder in dirs:
        current_data_folder = os.path.join(root, folder)
        print(f"Processing folder: {current_data_folder}")
        process_nc_files(current_data_folder, folder)


        for other_file in os.listdir(current_data_folder):
            other_file_path = os.path.join(current_data_folder, other_file)

            if not other_file.startswith(f"Sentinel-3_L2_{folder}_") or not other_file.endswith("_LST_reproj.tif"):
                if os.path.isfile(other_file_path):
                    os.remove(other_file_path)
                elif os.path.isdir(other_file_path):
                    shutil.rmtree(other_file_path)
        print(f"Cleaned up unnecessary files in {current_data_folder}")

print("All LST data saved and unnecessary files deleted successfully!")


shutil.rmtree(sentinel3_zips)
print(f"Deleted the folder: {sentinel3_zips}")








