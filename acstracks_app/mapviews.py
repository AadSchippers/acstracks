from django.conf import settings
import os
import gpxpy
import gpxpy.gpx
import folium
from folium.features import DivIcon
from decimal import *
from datetime import datetime
from pytz import timezone


def process_gpx_file(filename):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)
    points = []
    points_info = []
    previous_distance = -1
    previous_speed = -1
    timezone_info = timezone(settings.TIME_ZONE)   
    for track in gpx.tracks:
        for segment in track.segments:        
            for point in segment.points:
                for extension in point.extensions:
                    if extension.tag == 'distance':
                        distance = float(extension.text)
                    if extension.tag == 'speed':
                        speed = float(extension.text) * 3.6
                if distance < previous_distance:
                    distance = previous_distance
                    speed = previous_speed
                points.append(tuple([point.latitude,
                                    point.longitude,
                                     ]))
                points_info.append(tuple([point.time.astimezone(timezone_info).strftime("%H:%M:%S"),
                                    distance,
                                    round(speed, 2),
                                     ]))
                previous_distance = distance
                previous_speed = speed

    # print(points)
    ave_lat = sum(p[0] for p in points)/len(points)
    ave_lon = sum(p[1] for p in points)/len(points)

    # Load map centred on average coordinates
    my_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)

    min_lat = float(9999999)
    max_lat = float(-9999999)
    min_lon = float(9999999)
    max_lon = float(-9999999)
    for p in points:
        if min_lat > p[0]:
            min_lat = p[0]
        if max_lat < p[0]:
            max_lat = p[0]
        if min_lon > p[1]:
            min_lon = p[1]
        if max_lon < p[1]:
            max_lon = p[1]

    sw = tuple([min_lat, min_lon])
    ne = tuple([max_lat, max_lon])

    my_map.fit_bounds([sw, ne]) 


    # add a markers
    # for each in points:  
    #     folium.Marker(each).add_to(my_map)
    # folium.Marker(points[0], icon=folium.Icon(color='lightgray', icon='home', prefix='fa')).add_to(my_map)

    i = 0
    t0 = datetime.strptime(points_info[0][0], "%H:%M:%S")
    previous_marker_distance = 0

    # for x in range(int(len(points)/10), len(points), int(len(points)/11)):
    for x in range(len(points)):
        distance = float(points_info[x][1]) / 1000
        if distance < previous_marker_distance + 5:
            continue
        previous_marker_distance = distance
        i = i + 5
        tx = datetime.strptime(points_info[x][0], "%H:%M:%S")
        duration = tx - t0
        distance = float(points_info[x][1]) / 1000
        avgspeed = float((points_info[x][1] / duration.seconds) * 3.6)
        tooltip = 'Intermediate point '+ str(i)+ ' km, click for details'
        html = "<h3>Intermediate point "+ str(i)+" km</h3><table><tr><td><b>Time</b></td><td style='text-align:right'>"+points_info[x][0]+"</td></tr>"\
        "<tr><td><b>Duration</b></td><td style='text-align:right'>"+str(duration)+"</td></tr>"\
        "<tr><td><b>Distance</b></td><td style='text-align:right'>"+str(round(distance, 2))+ "</td></tr>"\
        "<tr><td><b>Current speed</b></td><td style='text-align:right'>"+str(points_info[x][2])+"</td></tr>"\
        "<tr><td><b>Average speed</b></td><td style='text-align:right'>"+str(round(avgspeed, 2))+ "</td></tr>"\
        "</table>"
        popup = folium.Popup(html, max_width=300)
        folium.Marker(points[x], tooltip=tooltip, popup=popup).add_to(my_map)

    # start marker
    tooltip = 'Start, click for details'
    html = "<h3>Start</h3><table><tr><td><b>Time</b></td><td style='text-align:right'>"+points_info[0][0]+"</td></tr>"\
    "</table>"
    popup = folium.Popup(html, max_width=300)
    folium.Marker(points[0], icon=folium.Icon(color='green'), tooltip=tooltip, popup=popup).add_to(my_map)

    # finish marker
    tooltip = 'Finish, click for details'
    tx = datetime.strptime(points_info[-1][0], "%H:%M:%S")
    duration = tx - t0
    avgspeed = float((points_info[-1][1] / duration.seconds) * 3.6)
    distance = float(points_info[-1][1]) / 1000

    html = "<h3>Finish</h3><table><tr><td><b>Time</b></td><td style='text-align:right'>"+points_info[-1][0]+"</td></tr>"\
    "<tr><td><b>Duration</b></td><td style='text-align:right'>"+str(duration)+"</td></tr>"\
    "<tr><td><b>Distance</b></td><td style='text-align:right'>"+str(round(distance, 2))+ "</td></tr>"\
    "<tr><td><b>Average speed</b></td><td style='text-align:right'>"+str(round(avgspeed, 2))+ "</td></tr>"\
    "</table>"
    popup = folium.Popup(html, max_width=300)
    folium.Marker(points[-1], icon=folium.Icon(color='red'), tooltip=tooltip, popup=popup).add_to(my_map)
 
    # folium.LayerControl(collapsed=True).add_to(my_map)

    # add lines
    folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            "map.html"
        )
    my_map.save(mapfilename)
 
    return
