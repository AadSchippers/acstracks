from django.conf import settings
import os
import gpxpy
import gpxpy.gpx
import folium
from folium.features import DivIcon
from decimal import *
from datetime import datetime
from pytz import timezone
from dateutil.parser import parse
import time
from haversine import haversine, Unit
from .models import Threshold


def process_gpx_file(request, filename, intermediate_points_selected, atrack=None, makemap=False):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)

    try:
        threshold = Threshold.objects.get(user=request.user)
        speedthreshold = threshold.speedthreshold
        elevationthreshold = threshold.elevationthreshold
    except:
        speedthreshold = settings.SPEEDTHRESHOLD
        elevationthreshold = settings.ELEVATIONTHRESHOLD

    points = []
    points_info = []
    starting_distance = 0
    previous_distance = 0
    previous_speed = -1
    previous_avgheartrate = 0
    no_hr_detected_seconds = 0
    no_cad_detected_seconds = 0
    cadence = 0
    avgcadence = None
    avgheartrate = None
    previous_avgcadence = 0
    timezone_info = timezone(settings.TIME_ZONE)   
    previous_point = None
    distance = None
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                distance = None
                speed = None        
                heartrate = 0
                cadence = 0
                for extension in point.extensions:
                    if extension.tag == 'distance':
                        distance = float(extension.text) - starting_distance
                    if extension.tag == 'speed':
                        speed = float(extension.text) * 3.6
                    if extension.tag in settings.HEARTRATETAGS:
                        heartrate = int(extension.text)
                    if extension.tag in settings.CADENCETAGS:
                        cadence = int(extension.text)
                    for TrackPointExtension in extension:
                        if TrackPointExtension.tag in settings.HEARTRATETAGS:
                            heartrate = int(TrackPointExtension.text)
                        if TrackPointExtension.tag in settings.CADENCETAGS:
                            cadence = int(TrackPointExtension.text)
                printspeed = speed
                if not distance:
                    point_distance = calculate_using_haversine(point, previous_point)
                    distance = previous_distance + point_distance
                    previous_distance = distance
                    speed = None

                previous_point = point
                x = len(points_info)
                if x > 0:
                    if distance < previous_distance:
                        distance = previous_distance
                        speed = previous_speed                    
                    t0 = datetime.strptime(points_info[0][0], "%Y-%m-%d %H:%M:%S")
                    tx = datetime.strptime(point.time.astimezone(timezone_info).strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
                    duration = tx - t0
                    txminus1 = datetime.strptime(points_info[x-1][0], "%Y-%m-%d %H:%M:%S")
                    previous_duration = txminus1 - t0
                    if not speed:
                        speed = (point_distance / (duration.seconds - previous_duration.seconds)) * 3.6
                    if speed <= speedthreshold and (not cadence or cadence == 0):
                        pass
                    else:
                        moving_duration = moving_duration + (duration - previous_duration)
                    if heartrate:
                        avgheartrate = (
                            (previous_avgheartrate * (previous_duration.seconds - no_hr_detected_seconds)) +
                            (
                                heartrate * (
                                    duration.seconds - previous_duration.seconds
                                    )
                            )
                        ) / (duration.seconds - no_hr_detected_seconds)
                        previous_avgheartrate = avgheartrate
                    else:
                        no_hr_detected_seconds = no_hr_detected_seconds + (duration.seconds - previous_duration.seconds)
                    if cadence:
                        avgcadence = (
                            (previous_avgcadence * (previous_duration.seconds - no_cad_detected_seconds)) +
                            (
                                cadence * (
                                    duration.seconds - previous_duration.seconds
                                    )
                            )
                        ) / (duration.seconds - no_cad_detected_seconds)
                        previous_avgcadence = avgcadence
                    else:
                        no_cad_detected_seconds = no_cad_detected_seconds + (duration.seconds - previous_duration.seconds)
                else:
                    starting_distance = distance
                    distance = 0
                    speed = 0
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
                    point.time.astimezone(timezone_info).strftime("%Y-%m-%d %H:%M:%S"),
                    distance,
                    duration,
                    moving_duration,
                    round(speed, 2),
                    heartrate,
                    avgheartrate,
                    cadence,
                    avgcadence,
                    round(point.elevation, 2),
                    ]))
                    
                previous_distance = distance
                previous_speed = speed

    if atrack:
        update_track(atrack, points_info, elevationthreshold)

    if makemap:
        make_map(points, points_info, filename, intermediate_points_selected)

    return


def update_track(atrack, points_info, elevationthreshold):

    last = len(points_info) - 1
    created_date = points_info[0][0]
    trkLength = float(points_info[last][1]) / 1000
    trkTimelength = time.strftime('%H:%M:%S', time.gmtime(int(points_info[last][3].seconds)))

    try:
        trkAvgspeed = float((points_info[last][1] / points_info[last][3].seconds) * 3.6)
    except:
        trkAvgspeed = 0
    try:
        trkAvgcadence = int(points_info[last][8])
    except:
        trkAvgcadence = None
    try:
        trkAvgheartrate = int(points_info[last][6])
    except:
        trkAvgheartrate = None

    trkMaxspeed = 0
    trkMaxcadence = 0
    trkMinheartrate = 999
    trkMaxheartrate = 0
    trkMaxcadence = 0
    totalascent = 0 
    totaldescent = 0 
    previous_elevation = points_info[0][9] 

    for point in points_info:
        if point[4] > trkMaxspeed: 
            trkMaxspeed = point[4]
        if point[5]:
            if point[5] > trkMaxheartrate: 
                trkMaxheartrate = point[5]
            if point[5] < trkMinheartrate: 
                trkMinheartrate = point[5]
        if point[7] > trkMaxcadence: 
            trkMaxcadence = point[7]
        if abs(point[9] - previous_elevation) > elevationthreshold:
            if point[9] > previous_elevation:
                totalascent = totalascent + (point[9] - previous_elevation)
            if point[9] < previous_elevation:
                totaldescent = totaldescent + (previous_elevation - point[9])
        previous_elevation = point[9]

    getcontext().prec = 2

    atrack.created_date = parse(created_date)
    atrack.length = round(trkLength, 2)
    atrack.timelength = trkTimelength
    atrack.avgspeed = round(trkAvgspeed, 2)
    atrack.maxspeed = round(trkMaxspeed, 2)
    atrack.totalascent = round(totalascent, 2)
    atrack.totaldescent = round(totaldescent, 2)
    atrack.avgcadence = trkAvgcadence
    atrack.maxcadence = trkMaxcadence
    atrack.avgheartrate = trkAvgheartrate
    atrack.minheartrate = trkMinheartrate
    atrack.maxheartrate = trkMaxheartrate

    atrack.save()

    return


def make_map(points, points_info, filename, intermediate_points_selected):

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
            speed = points_info[x][4]
            try:
                avgspeed = float((points_info[x][1] / moving_duration.seconds) * 3.6)
            except:
                avgspeed = 0
            heartrate = points_info[x][5]
            avgheartrate = points_info[x][6]
            cadence = points_info[x][7]
            avgcadence = points_info[x][8]
            tooltip_text = 'Intermediate point ' + str(i) + ' km, click for details'
            tooltip_style = 'color: #700394; font-size: 0.85vw'
            tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)

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
    tooltip_text = 'Start, click for details'
    tooltip_style = 'color: #700394; font-size: 0.85vw'
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<h3 style='color: #700394; font-weight: bold; font-size: 1.5vw'>Start</h3>" +
        "<table style='color: #700394; width: 100%; font-size: 0.85vw'><tr><td><b>Time</b></td>" +
        "<td style='text-align:right'>"+points_info[0][0]+"</td></tr>" +
        "</table>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(points[0], icon=folium.Icon(color='green'), tooltip=tooltip, popup=popup).add_to(my_map)

    # finish marker
    tooltip_text = 'Finish, click for details'
    tooltip_style = 'color: #700394; font-size: 0.85vw'
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    # tx = datetime.strptime(points_info[-1][0], "%H:%M:%S")
    # duration = tx - t0
    duration = points_info[-1][2]
    moving_duration = points_info[-1][3]
    avgspeed = float((points_info[-1][1] / moving_duration.seconds) * 3.6)
    distance = float(points_info[-1][1]) / 1000

    html = (
        "<h3 style='color: #700394; font-weight: bold; font-size: 1.5vw'>Finish</h3>"+
        "<table style='color: #700394; width: 100%; font-size: 0.85vw'>" +
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


def calculate_using_haversine(point, previous_point):
    distance = float(0.00)

    if previous_point:
        previous_location = (previous_point.latitude, previous_point.longitude)
        current_location = (point.latitude, point.longitude)
        distance = haversine(current_location, previous_location, unit='m')

    return distance


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
    line_title = "<h3 style='color: #700394; font-weight: bold; font-size: 1.5vw'>Intermediate point "+ intermediate_point+" km</h3>"
    line_table_start = "<table style='color: #700394; font-size: 0.85vw'>"
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
