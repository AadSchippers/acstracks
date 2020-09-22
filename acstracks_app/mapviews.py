from django.conf import settings
import os
import gpxpy
import gpxpy.gpx
import folium
from folium.features import DivIcon
from decimal import *
from datetime import datetime
from pytz import timezone


def process_gpx_file(filename, intermediate_points_selected):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)
    points = []
    points_info = []
    starting_distance = 0
    previous_distance = -1
    previous_speed = -1
    heartrate = 0
    previous_avgheartrate = 0
    cadence = 0
    previous_avgcadence = 0
    timezone_info = timezone(settings.TIME_ZONE)   
    for track in gpx.tracks:
        for segment in track.segments:        
            for point in segment.points:
                for extension in point.extensions:
                    if extension.tag == 'distance':
                        distance = float(extension.text) - starting_distance
                    if extension.tag == 'speed':
                        speed = float(extension.text) * 3.6
                    if extension.tag in settings.HEARTRATETAGS:
                        heartrate = int(extension.text)
                    if extension.tag in settings.CADENCETAGS:
                        cadence = int(extension.text)
                x = len(points_info)
                if x > 0:
                    if distance < previous_distance:
                        distance = previous_distance
                        speed = previous_speed
                    t0 = datetime.strptime(points_info[0][0], "%H:%M:%S")
                    tx = datetime.strptime(point.time.astimezone(timezone_info).strftime("%H:%M:%S"), "%H:%M:%S")
                    duration = tx - t0
                    txminus1 = datetime.strptime(points_info[x-1][0], "%H:%M:%S")
                    previous_duration = txminus1 - t0
                    if speed <= settings.SPEEDTHRESHOLD and (not cadence or cadence == 0):
                        pass
                    else:
                        moving_duration = moving_duration + (duration - previous_duration)
                    if heartrate:
                        avgheartrate = (
                            (previous_avgheartrate * previous_duration.seconds) +
                            (
                                heartrate * (
                                    duration.seconds - previous_duration.seconds
                                    )
                            )
                        ) / duration.seconds
                        previous_avgheartrate = avgheartrate
                    else:
                        avgheartrate = None
                    if cadence:
                        avgcadence = (
                            (previous_avgcadence * previous_duration.seconds) +
                            (
                                cadence * (
                                    duration.seconds - previous_duration.seconds
                                    )
                            )
                        ) / duration.seconds
                        previous_avgcadence = avgcadence
                    else:
                        avgcadence = None
                else:
                    starting_distance = distance
                    distance = 0
                    t0 = datetime.strptime("00:00:00", "%H:%M:%S")
                    duration = t0 - t0
                    moving_duration = duration
                    previous_duration = duration
                    avgheartrate = heartrate
                    previous_avgheartrate = heartrate
                    avgcadence = cadence
                    previous_avgcadence = cadence
                points.append(tuple([point.latitude,
                                    point.longitude,
                                     ]))

                points_info.append(tuple([
                    point.time.astimezone(timezone_info).strftime("%H:%M:%S"),
                    distance,
                    duration,
                    moving_duration,
                    round(speed, 2),
                    heartrate,
                    avgheartrate,
                    cadence,
                    avgcadence,
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
    previous_marker_distance = 0

    # for x in range(int(len(points)/10), len(points), int(len(points)/11)):
    ip = int(intermediate_points_selected)
    if ip > 0:
        for x in range(len(points)):
            distance = float(points_info[x][1]) / 1000
            if distance < previous_marker_distance + ip:
                continue
            previous_marker_distance = distance
            i = i + ip
            time = points_info[x][0]
            duration = points_info[x][2]
            moving_duration = points_info[x][3]
            distance = float(points_info[x][1]) / 1000
            speed = points_info[x][4]
            try:
                avgspeed = float((points_info[x][1] / moving_duration.seconds) * 3.6)
            except:
                avgspeed = 0
            heartrate = points_info[x][5]
            avgheartrate = points_info[x][6]
            cadence = points_info[x][7]
            avgcadence = points_info[x][8]
            tooltip = 'Intermediate point ' + str(i) + ' km, click for details'
            html_popup = make_html_popup(
                str(i),
                time,
                duration,
                moving_duration, 
                distance,
                speed,
                avgspeed,
                heartrate,
                avgheartrate,
                cadence,
                avgcadence,
                )
            popup = folium.Popup(html_popup, max_width=400)
            folium.Marker(points[x], tooltip=tooltip, popup=popup).add_to(my_map)

    # start marker
    tooltip = 'Start, click for details'
    html = (
        "<h3 style='color: #700394'>Start</h3>" +
        "<table  style='color: #700394; width: 100%'><tr><td><b>Time</b></td>" +
        "<td style='text-align:right'>"+points_info[0][0]+"</td></tr>" +
        "</table>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(points[0], icon=folium.Icon(color='green'), tooltip=tooltip, popup=popup).add_to(my_map)

    # finish marker
    tooltip = 'Finish, click for details'
    # tx = datetime.strptime(points_info[-1][0], "%H:%M:%S")
    # duration = tx - t0
    duration = points_info[-1][2]
    moving_duration = points_info[-1][3]
    avgspeed = float((points_info[-1][1] / moving_duration.seconds) * 3.6)
    distance = float(points_info[-1][1]) / 1000

    html = (
        "<h3 style='color: #700394'>Finish</h3>"+
        "<table style='color: #700394; width: 100%'>" +
        "<tr><td><b>Time</b></td><td style='text-align:right'>"+points_info[-1][0]+"</td></tr>" +
        "<tr><td><b>Distance</b></td><td style='text-align:right'>"+str(round(distance, 2))+"</td></tr>" +
        "<tr><td><b>Average speed</b></td><td style='text-align:right'>"+str(round(avgspeed, 2))+"</td></tr>" +
        "<tr><td><b>Duration</b></td><td style='text-align:right'>"+str(duration)+"</td></tr>" +
        "<tr><td><b>Duration while moving</b></td><td style='text-align:right'>"+str(moving_duration)+"</td></tr>" +
        "</table>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(points[-1], icon=folium.Icon(color='red'), tooltip=tooltip, popup=popup).add_to(my_map)
 
    # folium.LayerControl(collapsed=True).add_to(my_map)

    # add lines
    folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            os.path.splitext(filename)[0]+".html"
        )
    my_map.save(mapfilename)
 
    return


def make_html_popup(
        intermediate_point,
        time,
        duration,
        moving_duration,
        distance,
        speed,
        avgspeed,
        heartrate,
        avgheartrate,
        cadence,
        avgcadence,
    ):
    line_title = "<h3 style='color: #700394'>Intermediate point "+ intermediate_point+" km</h3>"
    line_table_start = "<table style='color: #700394'>"
    line_table_end = "</table>"
    line_time_distance = (
        "<tr><td><b>Time</b></td><td style='padding: 0 10px;text-align:right'>" +
        time+"</td>" +
        "<td><b>Distance</b></td><td style='padding: 0 10px;text-align:right'>" +
        str(round(distance, 2)) + "</td></tr>"
    )
    line_duration = (
        "<tr><td><b>Duration</b></td><td style='padding: 0 10px;text-align:right'>" +
        str(duration)+"</td><td><b>Duration while moving</b></td><td style='padding: 0 10px;text-align:right'>"+
        str(moving_duration)+"</td></tr>"
    )
    line_speed = (
        "<tr><td><b>Current speed</b></td><td style='padding: 0 10px;text-align:right'>" +
        str(speed)+"</td>" +
        "<td><b>Average speed</b></td><td style='padding: 0 10px;text-align:right'>" +
        str(round(avgspeed, 2)) +
        "</td></tr>"
    )
    if heartrate:
        line_heartrate = (
            "<tr><td><b>Current heartrate</b></td><td style='padding: 0 10px;text-align:right'>" +
            str(heartrate)+"</td>" +
            "<td><b>Average heartrate</b></td><td style='padding: 0 10px;text-align:right'>" +
            str(int(round(avgheartrate, 0))) +
            "</td></tr>"
        )
    else:
        line_heartrate = ""
    if cadence:
        line_cadence = (
            "<tr><td><b>Current cadence</b></td><td style='padding: 0 10px;text-align:right'>" +
            str(round(cadence, 0)) +"</td>" +
            "<td><b>Average cadence</b></td><td style='padding: 0 10px;text-align:right'>" +
            str(int(round(avgcadence, 0))) +
            "</td></tr>"
        )
    else:
        line_cadence = ""

    html_popup = (
        line_title +
        line_table_start +
        line_time_distance +
        line_duration +
        line_speed +
        line_heartrate +
        line_cadence +
        line_table_end
    )

    return html_popup
