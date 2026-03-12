import pandas as pd
import os
from bisect import bisect_left, bisect_right
#import piexif
from fractions import Fraction
import math
#from osgeo import gdal


def interpolate(x1: float, x2: float, y1: float, y2: float, x: float):

    #basic linear interpolation function

    return ((y2 - y1) * (x - x1))/(x2-x1) + y1

def create_image_df2(start_time,time_step,file_folder):

    #use this one if you already have a folder of images with a known time interval between them
    #assigns timestamps to each extracted frame and creates a dataframe containing image filenames and timestamps
    #start_time input format: YYYY-MM-DD HH:MM:SS.0000 in UTC
    #file folder should be the one created with the extract_frames function and should contain only image files

    filenames = [f for f in os.listdir(file_folder)] #creates list of filenames from folder

    datetime = pd.to_datetime(start_time) #converts input string to datetime object
    start_timestamp = datetime.timestamp() #converts datetime object to unix
    timestamps = [start_timestamp + i * time_step for i in range(len(filenames))]
    
    image_df = pd.DataFrame({'Filename': filenames, 'Timestamp': timestamps})
    #image_df['Timestamp'] = image_df['Timestamp'].apply(lambda x: f"{x:.4f}")
    return image_df

def generate_metadata(flight_df,image_df):
    
    # for each file in image_df, we find the two neighboring rows in the flight data and perform a linear interpolation on them
    # to estimate the latitude, longitude, altitude, and heading for the corresponding timestamp and add this data to image_df
    
    image_df['Latitude'] = None
    image_df['Longitude'] = None
    image_df['Altitude'] = None
    image_df['Heading'] = None

    image_df.loc[0,'Latitude'] = flight_df.loc[0,'latitude']
    image_df.loc[0,'Longitude'] = flight_df.loc[0,'longitude']
    image_df.loc[0,'Altitude'] = flight_df.loc[0,'altitude']
    image_df.loc[0,'Heading'] = flight_df.loc[0,'heading']
    
    for i in range(0,len(image_df.Timestamp)):
   
        target_time = image_df.Timestamp.iloc[i]

        insert_pos = bisect_left(flight_df['time'], target_time)

        if insert_pos == 0 or insert_pos >= len(flight_df):
            continue  # skip this row — no neighbors to interpolate

        lower_neighbor = flight_df['time'][insert_pos - 1]
        upper_neighbor = flight_df['time'][insert_pos]
        
        
        # lower_neighbor = flight_df['time'][bisect_left(flight_df['time'], image_df.Timestamp.iloc[i]) - 1]
        # upper_neighbor =  flight_df['time'][bisect_right(flight_df['time'], image_df.Timestamp.iloc[i])]
        
        ln_idx = flight_df.index[flight_df['time'] == lower_neighbor].item()       #index number of lower neighbor
        un_idx = flight_df.index[flight_df['time'] == upper_neighbor].item()       #index number of upper neighbor


        
        image_df.loc[i, 'Latitude'] = interpolate(flight_df['time'].iloc[ln_idx],
                                                  flight_df['time'].iloc[un_idx],
                                                  flight_df['latitude'].iloc[ln_idx],
                                                  flight_df['latitude'].iloc[un_idx],
                                                  image_df.Timestamp.iloc[i])
        
        image_df.loc[i, 'Longitude'] = interpolate(flight_df['time'].iloc[ln_idx],
                                                   flight_df['time'].iloc[un_idx],
                                                   flight_df['longitude'].iloc[ln_idx],
                                                   flight_df['longitude'].iloc[un_idx],
                                                   image_df.Timestamp.iloc[i])
        
        image_df.loc[i, 'Altitude'] = interpolate(flight_df['time'].iloc[ln_idx],
                                                  flight_df['time'].iloc[un_idx],
                                                  flight_df['altitude'].iloc[ln_idx], 
                                                  flight_df['altitude'].iloc[un_idx],
                                                  image_df.Timestamp.iloc[i])
        
        image_df.loc[i, 'Heading'] = interpolate(flight_df['time'].iloc[ln_idx], 
                                                 flight_df['time'].iloc[un_idx],
                                                 flight_df['heading'].iloc[ln_idx], 
                                                 flight_df['heading'].iloc[un_idx],
                                                 image_df.Timestamp.iloc[i])


def write_gps_to_jpeg(image_path, latitude, longitude, altitude, heading):
    #Writes GPS coordinates to the EXIF data of a JPEG image.

    # Convert decimal degrees to degrees, minutes, seconds format
    def convert_to_dms(decimal_degrees):
        degrees = int(decimal_degrees)
        minutes = int((decimal_degrees - degrees) * 60)
        #seconds = int((((decimal_degrees - degrees) * 60) - minutes) * 60)
    

        seconds = (decimal_degrees - degrees - minutes / 60) * 3600
        fraction = Fraction(seconds).limit_denominator(10000)
        
        return [(degrees,1), (minutes,1), (fraction.numerator, fraction.denominator)]


    
    lat_deg, lat_min, lat_sec = convert_to_dms(abs(latitude))
    lon_deg, lon_min, lon_sec = convert_to_dms(abs(longitude))
    alt_frac = Fraction(abs(altitude)).limit_denominator(1000)
    heading_frac = Fraction(heading).limit_denominator(1000)


    exif_dict = piexif.load(image_path)

    # Create GPS IFD (Image File Directory)
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if latitude >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: ((lat_deg), (lat_min), (lat_sec)),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if longitude >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: ((lon_deg), (lon_min), (lon_sec)),
        piexif.GPSIFD.GPSAltitudeRef: 0 if altitude >= 0 else 1,
        piexif.GPSIFD.GPSAltitude: (alt_frac.numerator, alt_frac.denominator),
        piexif.GPSIFD.GPSImgDirectionRef: b'T',  # T = True North
        piexif.GPSIFD.GPSImgDirection: (heading_frac.numerator, heading_frac.denominator)

    }

    exif_dict["GPS"] = gps_ifd

    # Dump the EXIF data into a binary format
    exif_bytes = piexif.dump(exif_dict)

    # Insert the EXIF data into the image
    piexif.insert(exif_bytes, image_path)






def batch_write_gps(file_folder,image_df):

    for i in range(len(image_df.Filename)):
        image_path = f"{file_folder}/{image_df.Filename[i]}"
        latitude = image_df.Latitude[i]
        longitude = image_df.Longitude[i]
        altitude = image_df.Altitude[i]
        heading = image_df.Heading[i]
        write_gps_to_jpeg(image_path, latitude, longitude,altitude,heading)

def tan_deg(degrees):
    return math.tan(math.radians(degrees))

def meters_to_degrees(width_m, height_m, center_lat_deg):
    meters_per_deg_lat = 111_320
    meters_per_deg_lon = 111_320 * math.cos(math.radians(center_lat_deg))
    delta_lat = height_m / meters_per_deg_lat
    delta_lon = width_m / meters_per_deg_lon
    return delta_lon, delta_lat

def convert_folder_to_geotiffs(input_folder, output_folder, image_df, hfov_deg, vfov_deg, epsg=4326):
    os.makedirs(output_folder, exist_ok=True)

    for i in range(len(image_df.Filename)):

        filename = image_df.iloc[i]['Filename']
        
        input_path = os.path.join(input_folder, image_df.Filename.iloc[i])
        output_name = os.path.splitext(filename)[0] + '.tif'
        output_path = os.path.join(output_folder, output_name)

        lat = image_df.Latitude.iloc[i]
        lon = image_df.Longitude.iloc[i]
        
        # Compute footprint in meters
        width_m = 2 * image_df.Altitude.iloc[i] * tan_deg(hfov_deg / 2)
        height_m = 2 * image_df.Altitude.iloc[i] * tan_deg(vfov_deg / 2)

        # Convert to degrees
        delta_lon, delta_lat = meters_to_degrees(width_m, height_m, lat)

        # Calculate bounding box
        xmin = lon - delta_lon / 2
        xmax = lon + delta_lon / 2
        ymin = lat - delta_lat / 2
        ymax = lat + delta_lat / 2

        # Build gdal_translate command
        cmd = f'gdal_translate -of GTiff -a_ullr {xmin} {ymax} {xmax} {ymin} -a_srs EPSG:{epsg} "{input_path}" "{output_path}"'
        print(f"Processing {image_df.Filename.iloc[i]} → {output_name}")
        os.system(cmd)

    print("Conversion complete.")