from django.conf import settings
from django.utils.timezone import make_aware
from django.contrib import messages
import os
import gpxpy
import gpxpy.gpx
import folium
from folium.features import DivIcon
from decimal import Decimal
from datetime import datetime
from pytz import timezone
from dateutil.parser import parse
import time
from haversine import haversine, Unit
from .models import Preference
import csv
from django.http import HttpResponse
from .exceptions import *
import math


def process_gpx_file(
    request, filename, intermediate_points_selected,
    atrack=None, map_filename=None, updatetrack=False,
    savecsv=False, downloadgpx=False
):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        "gpx",
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)

    try:
        preference = Preference.objects.get(user=request.user)
        colorscheme = preference.colorscheme
        speedthreshold = preference.speedthreshold
        elevationthreshold = preference.elevationthreshold
        maxspeedcappingfactor = preference.maxspeedcappingfactor
        maximum_heart_rate = preference.maximum_heart_rate
        resting_heart_rate = preference.resting_heart_rate
    except Exception:
        colorscheme = settings.DEFAULT_COLORSCHEME
        speedthreshold = settings.SPEEDTHRESHOLD
        elevationthreshold = settings.ELEVATIONTHRESHOLD
        maxspeedcappingfactor = settings.MAXSPEEDCAPPINGFACTOR
        maximum_heart_rate = settings.MAXIMUM_HEART_RATE
        resting_heart_rate = preference.RESTING_HEART_RATE

    heart_rate_reserve = maximum_heart_rate - resting_heart_rate
    maximum_zone1 = resting_heart_rate + Decimal(round((0.6 * float(heart_rate_reserve)), 0))
    maximum_zone2 = resting_heart_rate + Decimal(round((0.7 * float(heart_rate_reserve)), 0))
    maximum_zone3 = resting_heart_rate + Decimal(round((0.8 * float(heart_rate_reserve)), 0))
    maximum_zone4 = resting_heart_rate + Decimal(round((0.9 * float(heart_rate_reserve)), 0))

    allpoints = []
    previous_distance = 0
    previous_speed = -1
    previous_avgheartrate = 0
    no_hr_detected_seconds = 0
    no_cad_detected_seconds = 0
    cadence = 0
    avgcadence = None
    avgheartrate = None
    zone1 = 0
    zone2 = 0
    zone3 = 0
    zone4 = 0
    zone5 = 0
    previous_avgcadence = 0
    timezone_info = timezone(settings.TIME_ZONE)
    previous_point = None
    distance = None
    iFlagged = 0
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if not point.time:
                    raise AcsFileNoActivity

                distance = None
                speed = None
                heartrate = 0
                cadence = 0
                for extension in point.extensions:
                    if extension.tag in settings.HEARTRATETAGS:
                        heartrate = int(extension.text)
                    if extension.tag in settings.CADENCETAGS:
                        cadence = int(extension.text)
                    for TrackPointExtension in extension:
                        if TrackPointExtension.tag in settings.HEARTRATETAGS:
                            heartrate = int(TrackPointExtension.text)
                        if TrackPointExtension.tag in settings.CADENCETAGS:
                            cadence = int(TrackPointExtension.text)

                point_distance = calculate_using_haversine(
                    point, previous_point
                    )
                if not distance:
                    distance = previous_distance + point_distance
                    previous_distance = distance
                    speed = None

                previous_point = point
                x = len(allpoints)
                if x > 0:
                    if distance < previous_distance:
                        distance = previous_distance
                        speed = previous_speed
                        flagged = True
                        iFlagged += 1
                    else:
                        flagged = False
                    t0 = datetime.strptime(
                        allpoints[0]["created_date"], "%Y-%m-%d %H:%M:%S"
                        )
                    tx = datetime.strptime(point.time.astimezone(
                        timezone_info).strftime(
                        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
                        )
                    duration = tx - t0
                    txminus1 = datetime.strptime(
                        allpoints[x-1]["created_date"], "%Y-%m-%d %H:%M:%S"
                        )
                    previous_duration = txminus1 - t0

                    if not speed:
                        try:
                            speed = (
                                point_distance / (
                                    duration.seconds -
                                    previous_duration.seconds
                                    )
                                ) * 3.6
                        except Exception:
                            speed = 0

                    is_moving = (speed > settings.SPEEDTHRESHOLD) and (
                        not cadence or cadence > 0
                    )
                    if is_moving:
                        moving_duration = (
                            moving_duration + (duration - previous_duration)
                            )

                    if heartrate:
                        if is_moving:
                            if heartrate <= maximum_zone1:
                                zone1 = zone1 + (
                                    duration.seconds -
                                    previous_duration.seconds
                                )
                            elif heartrate <= maximum_zone2:
                                zone2 = zone2 + (
                                    duration.seconds -
                                    previous_duration.seconds
                                )
                            elif heartrate <= maximum_zone3:
                                zone3 = zone3 + (
                                    duration.seconds -
                                    previous_duration.seconds
                                )
                            elif heartrate <= maximum_zone4:
                                zone4 = zone4 + (
                                    duration.seconds -
                                    previous_duration.seconds
                                )
                            else:
                                zone5 = zone5 + (
                                    duration.seconds -
                                    previous_duration.seconds
                                )
                            avgheartrate = (
                                (previous_avgheartrate * (
                                    previous_duration.seconds -
                                    no_hr_detected_seconds
                                    )) +
                                (
                                    heartrate * (
                                        duration.seconds -
                                        previous_duration.seconds
                                        )
                                )
                            ) / (duration.seconds - no_hr_detected_seconds)
                            previous_avgheartrate = avgheartrate
                    else:
                        no_hr_detected_seconds = no_hr_detected_seconds + (
                            duration.seconds - previous_duration.seconds
                            )
                    if cadence:
                        avgcadence = (
                            (previous_avgcadence * (
                                previous_duration.seconds -
                                no_cad_detected_seconds
                                )) +
                            (
                                cadence * (
                                    duration.seconds -
                                    previous_duration.seconds
                                    )
                            )
                        ) / (duration.seconds - no_cad_detected_seconds)
                        previous_avgcadence = avgcadence
                    else:
                        no_cad_detected_seconds = (
                            no_cad_detected_seconds + (
                                duration.seconds - previous_duration.seconds
                                )
                        )
                else:
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
                    flagged = False

                apoint = {
                    "latitude": point.latitude,
                    "longitude": point.longitude,
                    "elevation": round(point.elevation, 2),
                    "created_date": point.time.astimezone(timezone_info).strftime(
                        "%Y-%m-%d %H:%M:%S"
                        ),
                    "distance": distance,
                    "duration": duration,
                    "moving_duration": moving_duration,
                    "speed": round(speed, 2),
                    "heartrate": heartrate,
                    "avgheartrate": avgheartrate,
                    "cadence": cadence,
                    "avgcadence": avgcadence,
                    "flagged": flagged,
                }
            
                allpoints.append(apoint)

                previous_distance = distance
                previous_speed = speed

    if iFlagged > 0:
        print(
            f"Filename: {filename}," +
            "number of points: {str(len(allpoints))}," +
            "points flagged {str(iFlagged)}"
            )

    if updatetrack:
        trackeffort = int(round(
            (math.sqrt((zone1 * 0.5) + (zone2 * 0.75) + (zone3 * 1) + (zone4 * 1.5) + (zone5 * 2)))
                * (avgheartrate * avgheartrate) / settings.TRACKEFFORTFACTOR, 0))
        update_track(
            atrack, allpoints, trackeffort, elevationthreshold, maxspeedcappingfactor
            )

    if map_filename:
        make_map(
            request,
            colorscheme,
            atrack,
            allpoints,
            filename,
            intermediate_points_selected,
            map_filename
            )

    if savecsv:
        return save_csv(request, atrack, allpoints)

    if downloadgpx:
        return download_gpx(request, atrack, allpoints)

    return


def update_track(
    atrack, allpoints, trackeffort, elevationthreshold, maxspeedcappingfactor
):

    last = len(allpoints) - 1
    created_date = allpoints[0]["created_date"]
    trkLength = float(allpoints[last]["distance"]) / 1000
    trkSeconds = int(allpoints[last]["moving_duration"].seconds)
    trkTimelength = time.strftime(
        '%H:%M:%S', time.gmtime(trkSeconds)
        )

    try:
        trkAvgspeed = float(
            (allpoints[last]["distance"] / allpoints[last]["moving_duration"].seconds) * 3.6
            )
    except Exception:
        trkAvgspeed = 0
    try:
        trkAvgcadence = int(allpoints[last]["avgcadence"])
    except Exception:
        trkAvgcadence = None
    try:
        trkAvgheartrate = int(allpoints[last]["avgheartrate"])
    except Exception:
        trkAvgheartrate = None

    trkMaxspeed = 0
    trkMaxspeed1 = 0
    trkMaxspeed2 = 0
    trkMaxspeed3 = 0
    trkMaxspeed4 = 0
    trkMaxspeedIndex = 0
    trkMaxspeedIndex1 = 0
    trkMaxspeedIndex2 = 0
    trkMaxspeedIndex3 = 0
    trkMaxspeedIndex4 = 0
    trkMinheartrate = 999
    trkMaxheartrate = 0
    trkMaxheartrateIndex = 0
    trkMaxcadence = 0
    trkMaxcadenceIndex = 0
    totalascent = 0
    totaldescent = 0
    previous_elevation = allpoints[0]["elevation"]

    trkBest20 = 0
    trkBest30 = 0
    trkBest60 = 0
    trkbest20_start_pointindex = 0
    trkbest20_end_pointindex = 0
    trkbest30_start_pointindex = 0
    trkbest30_end_pointindex = 0
    trkbest60_start_pointindex = 0
    trkbest60_end_pointindex = 0
    PointIndex1 = 0

    while PointIndex1 < len(allpoints)-1:
        avgMaxSpeed = 0
        try:
            avgMaxSpeed = (
                (
                    allpoints[PointIndex1]["speed"] +
                    allpoints[PointIndex1+1]["speed"] +
                    allpoints[PointIndex1+2]["speed"]
                ) / 3
            )
        except Exception:
            pass

        if avgMaxSpeed > trkMaxspeed1:
            trkMaxspeed1 = avgMaxSpeed
            trkMaxspeedIndex1 = PointIndex1
        elif avgMaxSpeed > trkMaxspeed2:
            trkMaxspeed2 = avgMaxSpeed
            trkMaxspeedIndex2 = PointIndex1
        elif avgMaxSpeed > trkMaxspeed3:
            trkMaxspeed3 = avgMaxSpeed
            trkMaxspeedIndex3 = PointIndex1
        elif avgMaxSpeed > trkMaxspeed4:
            trkMaxspeed4 = avgMaxSpeed
            trkMaxspeedIndex4 = PointIndex1

        if allpoints[PointIndex1]["heartrate"]:
            if allpoints[PointIndex1]["heartrate"] > trkMaxheartrate:
                trkMaxheartrate = allpoints[PointIndex1]["heartrate"]
                trkMaxheartrateIndex = PointIndex1
            if allpoints[PointIndex1]["heartrate"] < trkMinheartrate:
                trkMinheartrate = allpoints[PointIndex1]["heartrate"]
        if allpoints[PointIndex1]["cadence"] > trkMaxcadence:
            trkMaxcadence = allpoints[PointIndex1]["cadence"]
            trkMaxcadenceIndex = PointIndex1
        if (
            abs(allpoints[PointIndex1]["elevation"] - previous_elevation)
            > elevationthreshold
        ):
            if allpoints[PointIndex1]["elevation"] > previous_elevation:
                totalascent = totalascent + (
                    allpoints[PointIndex1]["elevation"] - previous_elevation
                    )
            if allpoints[PointIndex1]["elevation"] < previous_elevation:
                totaldescent = totaldescent + (
                    previous_elevation - allpoints[PointIndex1]["elevation"]
                    )
            previous_elevation = allpoints[PointIndex1]["elevation"]
        PointIndex2 = PointIndex1 + 1
        best20_done = False
        best30_done = False
        best60_done = False
        distance_0 = allpoints[PointIndex1]["distance"]
        time_0 = allpoints[PointIndex1]["moving_duration"].seconds
        while PointIndex2 < len(allpoints)-1:
            distance_t = allpoints[PointIndex2]["distance"] - distance_0
            time_t = allpoints[PointIndex2]["moving_duration"].seconds - time_0
            if not best20_done:
                if time_t >= 1200:
                    best20_done = True
                    try:
                        Best20 = float((distance_t / time_t) * 3.6)
                        if Best20 > trkBest20:
                            trkBest20 = Best20
                            trkbest20_start_pointindex = PointIndex1
                            trkbest20_end_pointindex = PointIndex2
                    except Exception:
                        pass
            if not best30_done:
                if time_t >= 1800:
                    best30_done = True
                    try:
                        Best30 = float((distance_t / time_t) * 3.6)
                        if Best30 > trkBest30:
                            trkBest30 = Best30
                            trkbest30_start_pointindex = PointIndex1
                            trkbest30_end_pointindex = PointIndex2
                    except Exception:
                        pass
            if not best60_done:
                if time_t >= 3600:
                    best60_done = True
                    try:
                        Best60 = float((distance_t / time_t) * 3.6)
                        if Best60 > trkBest60:
                            trkBest60 = Best60
                            trkbest60_start_pointindex = PointIndex1
                            trkbest60_end_pointindex = PointIndex2
                    except Exception:
                        pass
            PointIndex2 += 1
        PointIndex1 += 1

    if trkMaxspeed1 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed1
        trkMaxspeedIndex = trkMaxspeedIndex1
    elif trkMaxspeed2 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed2
        trkMaxspeedIndex = trkMaxspeedIndex2
    elif trkMaxspeed3 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed3
        trkMaxspeedIndex = trkMaxspeedIndex3
    else:
        trkMaxspeed = trkMaxspeed4
        trkMaxspeedIndex = trkMaxspeedIndex4

    getcontext().prec = 2

    atrack.created_date = make_aware(parse(created_date))
    atrack.length = round(trkLength, 2)
    atrack.timelength = trkTimelength
    atrack.avgspeed = round(trkAvgspeed, 2)
    atrack.best20 = round(trkBest20, 2)
    atrack.best20_start_pointindex = trkbest20_start_pointindex
    atrack.best20_end_pointindex = trkbest20_end_pointindex
    atrack.best30 = round(trkBest30, 2)
    atrack.best30_start_pointindex = trkbest30_start_pointindex
    atrack.best30_end_pointindex = trkbest30_end_pointindex
    atrack.best60 = round(trkBest60, 2)
    atrack.best60_start_pointindex = trkbest60_start_pointindex
    atrack.best60_end_pointindex = trkbest60_end_pointindex
    atrack.maxspeed = round(trkMaxspeed, 2)
    atrack.maxspeed_pointindex = trkMaxspeedIndex
    atrack.totalascent = round(totalascent, 0)
    atrack.totaldescent = round(totaldescent, 0)
    atrack.avgcadence = trkAvgcadence
    atrack.maxcadence = trkMaxcadence
    atrack.maxcadence_pointindex = trkMaxcadenceIndex
    atrack.avgheartrate = trkAvgheartrate
    atrack.minheartrate = trkMinheartrate
    atrack.maxheartrate = trkMaxheartrate
    atrack.maxheartrate_pointindex = trkMaxheartrateIndex
    if trackeffort:
        atrack.trackeffort = trackeffort

    atrack.save()

    return


def make_map(
    request, colorscheme, atrack, allpoints, filename,
    intermediate_points_selected, map_filename
):
    primary_color = settings.PRIMARY_COLOR[colorscheme]
    start_color = settings.START_COLOR[colorscheme]
    end_color = settings.END_COLOR[colorscheme]

    # print(points)
    ave_lat = sum(p["latitude"] for p in allpoints)/len(allpoints)
    ave_lon = sum(p["longitude"] for p in allpoints)/len(allpoints)

    # Load map centred on average coordinates
    my_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)

    min_lat = float(9999999)
    max_lat = float(-9999999)
    min_lon = float(9999999)
    max_lon = float(-9999999)
    for p in allpoints:
        if min_lat > p["latitude"]:
            min_lat = p["latitude"]
        if max_lat < p["latitude"]:
            max_lat = p["latitude"]
        if min_lon > p["longitude"]:
            min_lon = p["longitude"]
        if max_lon < p["longitude"]:
            max_lon = p["longitude"]

    sw = tuple([min_lat, min_lon])
    ne = tuple([max_lat, max_lon])

    my_map.fit_bounds([sw, ne])

    i = 0
    previous_marker_distance = 0

    ip = int(intermediate_points_selected)
    if ip > 0:
        for x in range(len(allpoints)):
            distance = float(allpoints[x]["distance"])

            if ip <= 10000:
                if distance < previous_marker_distance + ip:
                    continue
                previous_marker_distance = distance
                i = i + ip
                make_marker(my_map, colorscheme, allpoints, x, distance, i, 'Intermediate point ')

            if ip == 20000:
                if x > 0:
                    if x == atrack.best20_start_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Start best 20 minutes ')
                    elif x == atrack.best20_end_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'End best 20 minutes ')

            if ip == 30000:
                if x > 0:
                    if x == atrack.best30_start_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Start best 30 minutes ')
                    elif x == atrack.best30_end_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'End best 30 minutes ')

            if ip == 60000:
                if x > 0:
                    if x == atrack.best60_start_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Start best 60 minutes ')
                    elif x == atrack.best60_end_pointindex:
                        make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'End best 60 minutes ')

            if ip == 90000:
                if x > 0 and x == atrack.maxheartrate_pointindex:
                    make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Maximum heart rate ')

            if ip == 95000:
                if x > 0 and x == atrack.maxcadence_pointindex:
                    make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Maximum cadence ')

            if ip == 99999:
                if x > 0 and x == atrack.maxspeed_pointindex:
                    make_marker(my_map, colorscheme, allpoints, x, distance, distance, 'Maximum speed ', atrack.maxspeed)

    # start marker
    tooltip_text = "Start, click for details"
    tooltip_style = "color: " + primary_color + "; font-size: 0.85vw"
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<h3 style='color: " + primary_color + "; font-weight: bold; font-size: 1.5vw'>" +
        "Start</h3><table style='color: " + primary_color + "; width: 100%; " +
        "font-size: 0.85vw'><tr><td><b>Time </b></td>" +
        "<td style='text-align:right'>"+allpoints[0]["created_date"]+"</td></tr>" +
        "</table>"
    )
    first_point = [allpoints[0]["latitude"], allpoints[0]["longitude"]]
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        first_point,
        icon=folium.Icon(color=start_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    # finish marker
    tooltip_text = "Finish, click for details"
    tooltip_style = "color: " + primary_color + "; font-size: 0.85vw"
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    duration = allpoints[-1]["duration"]
    moving_duration = allpoints[-1]["moving_duration"]
    avgspeed = float((allpoints[-1]["distance"] / moving_duration.seconds) * 3.6)
    distance = float(allpoints[-1]["distance"]) / 1000

    html = (
        "<h3 style='color: " + primary_color + "; font-weight: bold; font-size: 1.5vw'>" +
        "Finish</h3><table style='color: " + primary_color + "; width: 100%; " +
        "font-size: 0.85vw'><tr><td><b>Time</b></td>" +
        "<td style='text-align:right'>"+allpoints[-1]["created_date"]+"</td></tr>" +
        "<tr><td><b>Distance</b></td><td style='text-align:right'>" +
        str(round(distance, 2))+"</td></tr>" +
        "<tr><td><b>Average speed</b></td><td style='text-align:right'>" +
        str(round(avgspeed, 2))+"</td></tr>" +
        "<tr><td><b>Duration</b></td><td style='text-align:right'>" +
        str(duration)+"</td></tr><tr><td><b>Duration while moving</b>" +
        "</td><td style='text-align:right'>" +
        str(moving_duration)+"</td></tr>" +
        "</table>"
    )
    last_point = [allpoints[-1]["latitude"], allpoints[-1]["longitude"]]
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        last_point,
        icon=folium.Icon(color=end_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    # folium.LayerControl(collapsed=True).add_to(my_map)

    # add lines
    points = []
    for point in allpoints:
        points.append([point["latitude"], point["longitude"]])
    folium.PolyLine(
        points,
        color=primary_color,
        weight=settings.MAP_LINE_WEIGHT,
        opacity=settings.NORMAL_OPACITY
        ).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def make_marker(my_map, colorscheme, allpoints, x, distance, i, tooltip_text, speed=None):
    primary_color = settings.PRIMARY_COLOR[colorscheme]

    time = allpoints[x]["created_date"]
    duration = allpoints[x]["duration"]
    moving_duration = allpoints[x]["moving_duration"]
    if not speed:
        speed = allpoints[x]["speed"]
    try:
        avgspeed = float(
            (allpoints[x]["distance"] / moving_duration.seconds) * 3.6
            )
    except Exception:
        avgspeed = 0
    heartrate = allpoints[x]["heartrate"]
    avgheartrate = allpoints[x]["avgheartrate"]
    cadence = allpoints[x]["cadence"]
    avgcadence = allpoints[x]["avgcadence"]
    popup_title_text = tooltip_text + 'at '
    tooltip_text = (
        tooltip_text +
        str(round(i/1000, 2)) + ' km, ' +
        str(speed) + ' km/h'
        )
    tooltip_style = (
        'color: ' +
        primary_color +
        '; font-size: 0.85vw'
    )
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)

    html_popup = make_html_popup(
        popup_title_text,
        colorscheme,
        str(round(i)),
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
    point_x = [allpoints[x]["latitude"], allpoints[x]["longitude"]]
    popup = folium.Popup(html_popup, max_width=400)
    folium.Marker(
        point_x,
        icon=folium.Icon(color=primary_color),
        tooltip=tooltip, popup=popup
        ).add_to(my_map)

    return


def save_csv(request, atrack, allpoints):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    csvfilename = os.path.splitext(atrack.displayfilename)[0]+".csv"
    response['Content-Disposition'] = 'attachment; filename="'+csvfilename+'"'

    writer = csv.writer(response)

    # write summerary first
    writer.writerow(['Summary'])

    writer.writerow(['displayfilename', atrack.displayfilename])
    writer.writerow(['creator', atrack.creator])
    writer.writerow(['created_date', atrack.created_date])
    writer.writerow(['name', atrack.name])
    writer.writerow(['profile', atrack.profile])
    writer.writerow(['length', atrack.length])
    writer.writerow(['timelength', atrack.timelength])
    writer.writerow(['avgspeed', atrack.avgspeed])
    writer.writerow(['maxspeed', atrack.maxspeed])
    writer.writerow(['totalascent', atrack.totalascent])
    writer.writerow(['totaldescent', atrack.totaldescent])
    if atrack.avgcadence:
        writer.writerow(['avgcadence', atrack.avgcadence])
        writer.writerow(['maxcadence', atrack.maxcadence])
    if atrack.avgheartrate:
        writer.writerow(['avgheartrate', atrack.avgheartrate])
        writer.writerow(['minheartrate', atrack.minheartrate])
        writer.writerow(['maxheartrate', atrack.maxheartrate])

    writer.writerow([''])

    writer.writerow([
        'longitude',
        'latitude',
        'elevation',
        'time',
        'distance (m)',
        'duration',
        'moving_duration',
        'speed (km/h)',
        'average speed (km/h)'
        'heartrate',
        'average heartrate',
        'cadence',
        'average cadence',
        ])

    row = 0
    while row < len(allpoints):
        moving_duration = allpoints[row]["moving_duration"]
        try:
            avgspeed = float(
                (allpoints[row]["distancde"] / moving_duration.seconds) * 3.6
                )
        except Exception:
            avgspeed = 0
        writer.writerow([
            allpoints[row]["latitude"],
            allpoints[row]["longitude"],
            round(allpoints[row]["elevation"], 2),
            allpoints[row]["created_date"],
            round(allpoints[row]["distance"], 2),
            allpoints[row]["duration"],
            allpoints[row]["moving_duration"],
            allpoints[row]["speed"],
            round(avgspeed, 2),
            allpoints[row]["heartrate"],
            int(allpoints[row]["avgheartrate"]),
            allpoints[row]["cadence"],
            int(allpoints[row]["avgcadence"]),
        ])
        row += 1

    return response


def download_gpx(request, atrack, allpoints):
    # Create the HttpResponse object with the appropriate header.
    response = HttpResponse(content_type='text/gpx')
    gpxfilename = os.path.splitext(atrack.displayfilename)[0]+".gpx"
    response['Content-Disposition'] = 'attachment; filename="'+gpxfilename+'"'

    gpx_timezone_info = timezone(settings.GPX_TIME_ZONE)

    writer = csv.writer(response)

    writer.writerow([str("<?xml version='1.0' encoding='UTF-8'?>")])

    writer.writerow([
        str(
            "<gpx version='1.1' creator='AcsTracks' " +
            "xmlns='http://www.topografix.com/GPX/1/1' " +
            "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' " +
            "xsi:schemaLocation='http://www.topografix.com/GPX/1/1 " +
            "http://www.topografix.com/GPX/1/1/gpx.xsd'>"
        )
        ])
    writer.writerow([str("  <metadata>")])
    writer.writerow([str(
        "    <time>" +
        make_aware(parse(allpoints[0]["created_date"])).astimezone(
            gpx_timezone_info
            ).strftime("%Y-%m-%dT%H:%M:%SZ")+"</time>")]
        )
    writer.writerow([str("  </metadata>")])
    writer.writerow([str("  <trk>")])
    writer.writerow([str("    <name>"+atrack.name+"</name>")])
    writer.writerow([str("    <extensions>")])
    writer.writerow([str("      <profile>"+atrack.profile+"</profile>")])
    writer.writerow([str("    </extensions>")])
    writer.writerow([str("    <trkseg>")])

    row = 0
    while row < len(allpoints):
        if allpoints[row]["flagged"] is False:
            writer.writerow([str(
                "      <trkpt lat='" +
                str(allpoints[row]["latitude"]) +
                "' lon='"+str(allpoints[row]["longitude"])+"'>")]
                )
            writer.writerow([str(
                "        <ele>"+str(round(allpoints[row]["elevation"], 2))+"</ele>")]
                )
            if request.user == atrack.user:
                writer.writerow([str(
                    "        <time>" +
                    make_aware(parse(
                        allpoints[row]["created_date"])
                        ).astimezone(gpx_timezone_info).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                        ) + "</time>")]
                    )
                writer.writerow([str("        <extensions>")])
                writer.writerow([str(
                    "          <heartrate>" +
                    str(allpoints[row]["heartrate"]) +
                    "</heartrate>")]
                    )
                writer.writerow([str(
                    "          <cadence>" +
                    str(allpoints[row]["cadence"]) +
                    "</cadence>")]
                    )
                writer.writerow([str("        </extensions>")])
            writer.writerow([str("      </trkpt>")])
        row += 1

    writer.writerow([str("    </trkseg>")])
    writer.writerow([str("  </trk>")])
    writer.writerow([str("</gpx>")])

    return response


def calculate_using_haversine(point, previous_point):
    distance = float(0.00)

    if previous_point:
        previous_location = (previous_point.latitude, previous_point.longitude)
        current_location = (point.latitude, point.longitude)
        distance = haversine(current_location, previous_location, unit='m')

    return distance


def make_html_popup(
        title_text,
        colorscheme,
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
    primary_color = settings.PRIMARY_COLOR[colorscheme]
    line_title = (
        "<h3 style='color: " + primary_color + "; font-weight: bold; " +
        "font-size: 1.5vw'>" + title_text +
        str(round(int(intermediate_point)/1000, 2))+" km</h3>"
    )
    line_table_start = (
        "<table style='color: " + primary_color + "; font-size: 0.85vw; width: 100%'>"
    )
    line_table_end = "</table>"
    line_time_distance = (
        "<tr><td><b>Time</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        time+"</td>" +
        "<td><b>Distance</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        str(round(distance/1000, 2)) + "</td></tr>"
    )
    line_duration = (
        "<tr><td><b>Duration</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        str(duration) +
        "</td><td><b>Duration while moving</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        str(moving_duration)+"</td></tr>"
    )
    line_speed = (
        "<tr><td><b>Current speed</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        str(speed)+"</td>" +
        "<td><b>Average speed</b></td>" +
        "<td style='padding: 0 10px;text-align:right'>" +
        str(round(avgspeed, 2)) +
        "</td></tr>"
    )
    if heartrate:
        line_heartrate = (
            "<tr><td><b>Current heart rate</b></td>" +
            "<td style='padding: 0 10px;text-align:right'>" +
            str(heartrate)+"</td>" +
            "<td><b>Average heart rate</b></td>" +
            "<td style='padding: 0 10px;text-align:right'>" +
            str(int(round(avgheartrate, 0))) +
            "</td></tr>"
        )
    else:
        line_heartrate = ""
    if cadence:
        line_cadence = (
            "<tr><td><b>Current cadence</b></td>" +
            "<td style='padding: 0 10px;text-align:right'>" +
            str(round(cadence, 0)) + "</td>" +
            "<td><b>Average cadence</b></td>" +
            "<td style='padding: 0 10px;text-align:right'>" +
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


def gather_heatmap_data(request, filename, trackname=None, map_filename=None):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT + "/gpx",
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)

    try:
        allpoints = []
        atrack = {}
        timezone_info = timezone(settings.TIME_ZONE)
        previous_point = None
        distance = 0
        for track in gpx.tracks:
            if not trackname:
                trackname = track.name
            for segment in track.segments:
                for point in segment.points:
                    allpoints.append({
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "elevation": point.elevation, 
                        })

                    point_distance = calculate_using_haversine(
                        point, previous_point
                        )
                    distance += point_distance

                    previous_point = point

            atrack["trackname"] = trackname
            atrack["distance"] = round(distance/1000, 2)
            atrack["allpoints"] = allpoints
    except Exception:
        atrack = None

    return atrack


def make_heatmap(
        request, tracks, map_filename,
        colorscheme=settings.DEFAULT_COLORSCHEME,
        opacity=settings.HEATMAP_OPACITY,
        weight=settings.HEATMAP_LINE_WEIGHT,
        show_markers=False
        ):
    primary_color = settings.PRIMARY_COLOR[colorscheme]

    ave_lats = []
    ave_lons = []
    try:
        for t in tracks:
            ave_lats.append(
                sum(float(p["latidute"]) for p in t["allpoints"])/len(t["allpoints"])
                )
            ave_lons.append(
                sum(float(p["longitude"]) for p in t["allpoints"])/len(t["allpoints"])
                )

        ave_lat = sum(float(p) for p in ave_lats) / len(ave_lats)
        ave_lon = sum(float(p) for p in ave_lons) / len(ave_lons)

        # Load map centred on average coordinates
        my_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)
    except Exception:
        my_map = folium.Map(zoom_start=12)

    min_lat = float(9999999)
    max_lat = float(-9999999)
    min_lon = float(9999999)
    max_lon = float(-9999999)
    for t in tracks:
        for p in t["allpoints"]:
            if min_lat > p["latitude"]:
                min_lat = p["latitude"]
            if max_lat < p["latitude"]:
                max_lat = p["latitude"]
            if min_lon > p["longitude"]:
                min_lon = p["longitude"]
            if max_lon < p["longitude"]:
                max_lon = p["longitude"]

    sw = tuple([min_lat, min_lon])
    ne = tuple([max_lat, max_lon])

    my_map.fit_bounds([sw, ne])

    allpoints = []
    for track in tracks:
        for p in track["allpoints"]:
            allpoints.append(tuple([p["latitude"], p["longitude"]]))

    for track in tracks:
        my_map = draw_heatmap(request, my_map, track, colorscheme, opacity, weight, show_markers)

    folium.LayerControl(collapsed=True).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def draw_heatmap(request, my_map, track, colorscheme, opacity, weight, show_markers):
    primary_color = settings.PRIMARY_COLOR[colorscheme]
    start_color = settings.START_COLOR[colorscheme]
    end_color = settings.END_COLOR[colorscheme]

    allpoints = []
    for p in track["allpoints"]:
        allpoints.append([p["latitude"], p["longitude"]])

    if show_markers:
        # start marker
        tooltip_text = "Start " + track["trackname"]
        tooltip_style = "color: " + primary_color + "; font-size: 0.85vw"
        tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
        folium.Marker(
            allpoints[0],
            icon=folium.Icon(color=start_color),
            tooltip=tooltip
            ).add_to(my_map)

        # finish marker
        tooltip_text = "Finish " + track["trackname"]
        tooltip_style = "color: " + primary_color + "; font-size: 0.85vw"
        tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
        folium.Marker(
            allpoints[-1],
            icon=folium.Icon(color=end_color),
            tooltip=tooltip
            ).add_to(my_map)

    # add lines
    folium.PolyLine(
        allpoints, color=primary_color, weight=weight, opacity=opacity
        ).add_to(my_map)

    return my_map
