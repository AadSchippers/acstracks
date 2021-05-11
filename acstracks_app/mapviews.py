from django.conf import settings
from django.utils.timezone import make_aware
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
from .models import Preference
import csv
from django.http import HttpResponse


def process_gpx_file(
    request, filename, intermediate_points_selected,
    atrack=None, map_filename=None, savecsv=False, downloadgpx=False
):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)

    try:
        preference = Preference.objects.get(user=request.user)
        speedthreshold = preference.speedthreshold
        elevationthreshold = preference.elevationthreshold
        maxspeedcappingfactor = preference.maxspeedcappingfactor
    except Exception:
        speedthreshold = settings.SPEEDTHRESHOLD
        elevationthreshold = settings.ELEVATIONTHRESHOLD
        maxspeedcappingfactor = settings.MAXSPEEDCAPPINGFACTOR

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
    iFlagged = 0
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
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
                printspeed = speed

                point_distance = calculate_using_haversine(
                    point, previous_point
                    )
                if not distance:
                    distance = previous_distance + point_distance
                    previous_distance = distance
                    speed = None

                previous_point = point
                x = len(points_info)
                if x > 0:
                    if distance < previous_distance:
                        distance = previous_distance
                        speed = previous_speed
                        flagged = True
                        iFlagged += 1
                    else:
                        flagged = False
                    t0 = datetime.strptime(
                        points_info[0][0], "%Y-%m-%d %H:%M:%S"
                        )
                    tx = datetime.strptime(point.time.astimezone(
                        timezone_info).strftime(
                        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
                        )
                    duration = tx - t0
                    txminus1 = datetime.strptime(
                        points_info[x-1][0], "%Y-%m-%d %H:%M:%S"
                        )
                    previous_duration = txminus1 - t0

                    if not speed:
                        speed = (
                            point_distance / (
                                duration.seconds - previous_duration.seconds
                                )
                            ) * 3.6

                    if speed <= speedthreshold and (
                        not cadence or cadence == 0
                    ):
                        pass
                    else:
                        moving_duration = (
                            moving_duration + (duration - previous_duration)
                            )

                    if heartrate:
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
                    flagged = False

                points.append(tuple([point.latitude,
                                    point.longitude]))

                points_info.append(tuple([
                    point.time.astimezone(timezone_info).strftime(
                        "%Y-%m-%d %H:%M:%S"
                        ),
                    distance,
                    duration,
                    moving_duration,
                    round(speed, 2),
                    heartrate,
                    avgheartrate,
                    cadence,
                    avgcadence,
                    round(point.elevation, 2),
                    flagged,
                   ]))

                previous_distance = distance
                previous_speed = speed

    if iFlagged > 0:
        print(
            f"Filename: {filename}," +
            "number of points: {str(len(points))}," +
            "points flagged {str(iFlagged)}"
            )

    if atrack:
        update_track(
            atrack, points_info, elevationthreshold, maxspeedcappingfactor
            )

    if map_filename:
        make_map(
            request,
            points,
            points_info,
            filename,
            intermediate_points_selected,
            map_filename
            )

    if savecsv:
        return save_csv(request, atrack, points, points_info)

    if downloadgpx:
        return download_gpx(request, atrack, points, points_info)

    return


def update_track(
    atrack, points_info, elevationthreshold, maxspeedcappingfactor
):

    last = len(points_info) - 1
    created_date = points_info[0][0]
    trkLength = float(points_info[last][1]) / 1000
    trkTimelength = time.strftime(
        '%H:%M:%S', time.gmtime(int(points_info[last][3].seconds))
        )

    try:
        trkAvgspeed = float(
            (points_info[last][1] / points_info[last][3].seconds) * 3.6
            )
    except Exception:
        trkAvgspeed = 0
    try:
        trkAvgcadence = int(points_info[last][8])
    except Exception:
        trkAvgcadence = None
    try:
        trkAvgheartrate = int(points_info[last][6])
    except Exception:
        trkAvgheartrate = None

    trkMaxspeed = 0
    trkMaxspeed1 = 0
    trkMaxspeed2 = 0
    trkMaxspeed3 = 0
    trkMaxspeed4 = 0
    trkMaxcadence = 0
    trkMinheartrate = 999
    trkMaxheartrate = 0
    trkMaxcadence = 0
    totalascent = 0
    totaldescent = 0
    previous_elevation = points_info[0][9]

    PointIndex = 0
    while PointIndex < len(points_info):
        avgMaxSpeed = 0
        try:
            avgMaxSpeed = (
                (
                    points_info[PointIndex][4] +
                    points_info[PointIndex+1][4] +
                    points_info[PointIndex+2][4]
                ) / 3
            )
        except Exception:
            pass
        if avgMaxSpeed > trkMaxspeed1:
            trkMaxspeed1 = avgMaxSpeed
        elif avgMaxSpeed > trkMaxspeed2:
            trkMaxspeed2 = avgMaxSpeed
        elif avgMaxSpeed > trkMaxspeed3:
            trkMaxspeed3 = avgMaxSpeed
        elif avgMaxSpeed > trkMaxspeed4:
            trkMaxspeed4 = avgMaxSpeed
        PointIndex = PointIndex + 1

    if trkMaxspeed1 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed1
    elif trkMaxspeed2 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed2
    elif trkMaxspeed3 <= trkMaxspeed4 * float(maxspeedcappingfactor):
        trkMaxspeed = trkMaxspeed3
    else:
        trkMaxspeed = trkMaxspeed4

    for point in points_info:
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

    atrack.created_date = make_aware(parse(created_date))
    atrack.length = round(trkLength, 2)
    atrack.timelength = trkTimelength
    atrack.avgspeed = round(trkAvgspeed, 2)
    atrack.maxspeed = round(trkMaxspeed, 2)
    atrack.totalascent = round(totalascent, 0)
    atrack.totaldescent = round(totaldescent, 0)
    atrack.avgcadence = trkAvgcadence
    atrack.maxcadence = trkMaxcadence
    atrack.avgheartrate = trkAvgheartrate
    atrack.minheartrate = trkMinheartrate
    atrack.maxheartrate = trkMaxheartrate

    atrack.save()

    return


def make_map(
    request, points, points_info, filename,
    intermediate_points_selected, map_filename
):

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

    i = 0
    previous_marker_distance = 0

    ip = int(intermediate_points_selected)
    if ip > 0:
        for x in range(len(points)):
            distance = float(points_info[x][1])
            if distance < previous_marker_distance + ip:
                continue
            previous_marker_distance = distance
            i = i + ip
            time = points_info[x][0]
            duration = points_info[x][2]
            moving_duration = points_info[x][3]
            speed = points_info[x][4]
            try:
                avgspeed = float(
                    (points_info[x][1] / moving_duration.seconds) * 3.6
                    )
            except Exception:
                avgspeed = 0
            heartrate = points_info[x][5]
            avgheartrate = points_info[x][6]
            cadence = points_info[x][7]
            avgcadence = points_info[x][8]
            tooltip_text = (
                'Intermediate point ' +
                str(i/1000) + ' km, ' +
                str(speed) + ' km/h'
                )
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
            folium.Marker(
                points[x],
                icon=folium.Icon(color=settings.MARKER_COLOR),
                tooltip=tooltip, popup=popup
                ).add_to(my_map)

    # start marker
    tooltip_text = 'Start, click for details'
    tooltip_style = 'color: #700394; font-size: 0.85vw'
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<h3 style='color: #700394; font-weight: bold; font-size: 1.5vw'>" +
        "Start</h3><table style='color: #700394; width: 100%; " +
        "font-size: 0.85vw'><tr><td><b>Time</b></td>" +
        "<td style='text-align:right'>"+points_info[0][0]+"</td></tr>" +
        "</table>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[0],
        icon=folium.Icon(color=settings.START_COLOR),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

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
        "<h3 style='color: #700394; font-weight: bold; font-size: 1.5vw'>" +
        "Finish</h3><table style='color: #700394; width: 100%; " +
        "font-size: 0.85vw'><tr><td><b>Time</b></td>" +
        "<td style='text-align:right'>"+points_info[-1][0]+"</td></tr>" +
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
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[-1],
        icon=folium.Icon(color=settings.END_COLOR),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    # folium.LayerControl(collapsed=True).add_to(my_map)

    # add lines
    folium.PolyLine(
        points, color=settings.LINE_COLOR, weight=2.5, opacity=1
        ).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def save_csv(request, atrack, points, points_info):
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
        'heartrate',
        'average heartrate',
        'cadence',
        'mincadence',
        ])

    row = 0
    while row < len(points):
        writer.writerow([
            points[row][0],
            points[row][1],
            round(points_info[row][9], 2),
            points_info[row][0],
            round(points_info[row][1], 2),
            points_info[row][2],
            points_info[row][3],
            points_info[row][4],
            points_info[row][5],
            int(points_info[row][6]),
            points_info[row][7],
            int(points_info[row][8]),
        ])
        row += 1

    return response


def download_gpx(request, atrack, points, points_info):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    gpxfilename = os.path.splitext(atrack.displayfilename)[0]+".gpx"
    response['Content-Disposition'] = 'attachment; filename="'+gpxfilename+'"'

    gpx_timezone_info = timezone(settings.GPX_TIME_ZONE)

    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

    writer = csv.writer(response)

    writer.writerow([str("<?xml version='1.0' encoding='UTF-8'?>")])

    writer.writerow([
        str(
            "<gpx version='1.1' creator='AcsTracks' " +
            "xmlns='http://www.topografix.com/GPX/1/1'" +
            "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' " +
            "xsi:schemaLocation='http://www.topografix.com/GPX/1/1 " +
            "http://www.topografix.com/GPX/1/1/gpx.xsd'>"
        )
        ])
    writer.writerow([str("  <metadata>")])
    writer.writerow([str(
        "    <time>" +
        make_aware(parse(points_info[0][0])).astimezone(
            gpx_timezone_info
            ).strftime("%Y-%m-%dT%H:%M:%SZ")+"</time>")]
        )
    writer.writerow([str("  </metadata>")])
    writer.writerow([str("  <trk>")])
    writer.writerow([str("    <name>"+atrack.name+"</name>")])
    writer.writerow([str("    <trkseg>")])

    row = 0
    while row < len(points):
        if points_info[row][10] is False:
            writer.writerow([str(
                "      <trkpt lat='" +
                str(points[row][0]) +
                "' lon='"+str(points[row][1])+"'>")]
                )
            writer.writerow([str(
                "        <ele>"+str(round(points_info[row][9], 2))+"</ele>")]
                )
            writer.writerow([str(
                "        <time>" +
                make_aware(parse(
                    points_info[row][0])
                    ).astimezone(gpx_timezone_info).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                    ) + "</time>")]
                )
            writer.writerow([str("        <extensions>")])
            if preference.gpx_contains_heartrate:
                writer.writerow([str(
                    "          <heartrate>" +
                    str(points_info[row][5]) +
                    "</heartrate>")]
                    )
            if preference.gpx_contains_cadence:
                writer.writerow([str(
                    "          <cadence>" +
                    str(points_info[row][7]) +
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
    line_title = (
        "<h3 style='color: #700394; font-weight: bold; " +
        "font-size: 1.5vw'>Intermediate point " +
        str(int(intermediate_point)/1000)+" km</h3>"
    )
    line_table_start = "<table style='color: #700394; font-size: 0.85vw'>"
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
            "<tr><td><b>Current heartrate</b></td>" +
            "<td style='padding: 0 10px;text-align:right'>" +
            str(heartrate)+"</td>" +
            "<td><b>Average heartrate</b></td>" +
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


def gather_heatmap_data(request, filename, map_filename=None):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)

    try:
        points = []
        atrack = {}
        timezone_info = timezone(settings.TIME_ZONE)
        previous_point = None
        distance = 0
        trackname = ""
        for track in gpx.tracks:
            trackname = track.name
            for segment in track.segments:
                for point in segment.points:
                    points.append(tuple([point.latitude,
                                        point.longitude,
                                        point.elevation, ]))

                    point_distance = calculate_using_haversine(
                        point, previous_point
                        )
                    distance += point_distance

                    previous_point = point

            atrack["trackname"] = trackname
            atrack["distance"] = round(distance/1000, 2)
            atrack["points"] = points
    except Exception:
        atrack = None

    return atrack


def make_heatmap(request, tracks, map_filename):
    ave_lats = []
    ave_lons = []
    try:
        for t in tracks:
            ave_lats.append(sum(float(p[0]) for p in t["points"])/len(t["points"]))
            ave_lons.append(sum(float(p[1]) for p in t["points"])/len(t["points"]))

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
        for p in t["points"]:
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

    points = []
    for track in tracks:
        for p in track["points"]:
            points.append(tuple([p[0], p[1]]))

    for track in tracks:
        my_map = draw_heatmap(request, my_map, track)

    folium.LayerControl(collapsed=True).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def draw_heatmap(request, my_map, track):
    points = []
    for p in track["points"]:
        points.append(tuple([p[0], p[1]]))

    # add lines and markers
    folium.PolyLine(
        points, color=settings.HEATMAP_LINE_COLOR, weight=2.5, opacity=0.5
        ).add_to(my_map)

    return my_map
