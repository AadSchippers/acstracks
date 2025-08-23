from django.conf import settings
import os
from django.contrib.messages import get_messages
import gpxpy
import gpxpy.gpx
import folium
from django.shortcuts import render, redirect
from folium.features import DivIcon
from decimal import *
from datetime import datetime
from pytz import timezone
from dateutil.parser import parse
import time
from haversine import haversine, Unit
from django.http import HttpResponse
import io
import copy


def process_segment(
    allpoints,
    elevationthreshold,
    maxspeedcappingfactor,
    start_segment=0,
    end_segment=99999999,
):

    if end_segment >= len(allpoints):
        end_segment = len(allpoints) - 1

#############
    last = len(allpoints) - 1
    segLength = float(allpoints[end_segment]["distance"] - allpoints[start_segment]["distance"]) / 1000
    segMovingSeconds = int(allpoints[end_segment]["moving_duration"].seconds) - int(allpoints[start_segment]["moving_duration"].seconds)
    segMovingDuration = time.strftime(
        '%H:%M:%S', time.gmtime(segMovingSeconds)
        )
    segSeconds = int(allpoints[end_segment]["duration"].seconds) - int(allpoints[start_segment]["duration"].seconds)
    segDuration = time.strftime(
        '%H:%M:%S', time.gmtime(segSeconds)
        )

    try:
        segAvgspeed = float(
            (segLength / segMovingSeconds) * 3600
            )
    except Exception:
        segAvgspeed = 0

    segMaxspeed = 0
    segMaxspeed1 = 0
    segMaxspeed2 = 0
    segMaxspeed3 = 0
    segMaxspeed4 = 0
    segMaxheartrate = 0
    segMaxcadence = 0
    totalascent = 0
    totaldescent = 0
    previous_elevation = None
    PointIndex1 = start_segment

    while PointIndex1 < end_segment:
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

        if avgMaxSpeed > segMaxspeed1:
            segMaxspeed1 = avgMaxSpeed
        elif avgMaxSpeed > segMaxspeed2:
            segMaxspeed2 = avgMaxSpeed
        elif avgMaxSpeed > segMaxspeed3:
            segMaxspeed3 = avgMaxSpeed
        elif avgMaxSpeed > segMaxspeed4:
            segMaxspeed4 = avgMaxSpeed

        if allpoints[PointIndex1]["heartrate"]:
            if allpoints[PointIndex1]["heartrate"] > segMaxheartrate:
                segMaxheartrate = allpoints[PointIndex1]["heartrate"]
        if allpoints[PointIndex1]["cadence"] > segMaxcadence:
            segMaxcadence = allpoints[PointIndex1]["cadence"]

        try:
            if allpoints[PointIndex1]["elevation"]:
                if not previous_elevation:
                    try:
                        previous_elevation = allpoints[PointIndex1]["elevation"]
                    except Exception:
                        pass
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
        except Exception:
            pass

        PointIndex1 += 1

    if segMaxspeed1 <= segMaxspeed4 * float(maxspeedcappingfactor):
        segMaxspeed = segMaxspeed1
    elif segMaxspeed2 <= segMaxspeed4 * float(maxspeedcappingfactor):
        segMaxspeed = segMaxspeed2
    elif segMaxspeed3 <= segMaxspeed4 * float(maxspeedcappingfactor):
        segMaxspeed = segMaxspeed3
    else:
        segMaxspeed = segMaxspeed4

    getcontext().prec = 2

    asegment = {
        "length":  round(segLength, 2),
        "movingduration": segMovingDuration,
        "duration": segDuration,
        "avgspeed": round(segAvgspeed, 2),
        "maxspeed": round(segMaxspeed, 2),
        "totalascent": round(totalascent, 0),
        "totaldescent": round(totaldescent, 0),
        "maxcadence": segMaxcadence,
        "maxheartrate": segMaxheartrate,
    }
#############

    return asegment


def segments_make_map(
    request, colorscheme, atrack, allpoints, map_filename, start_segment, end_segment
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

    # add lines
    points = []
    for point in allpoints:
        points.append([point["latitude"], point["longitude"]])
    folium.PolyLine(
        points,
        color=primary_color,
        weight=2.5,
        opacity=1
        ).add_to(my_map)

    my_map = draw_map(
        request,
        my_map,
        atrack,
        allpoints,
        primary_color,
        start_color,
        end_color,
        start_segment,
        end_segment,
        )

    folium.LayerControl(collapsed=True).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def draw_map(
    request, my_map, atrack, allpoints, primary_color, start_color, end_color,
    start_segment, end_segment
):
    if end_segment > len(allpoints) - 1:
        end_segment = len(allpoints) - 1

    points = []
    for p in allpoints:
        points.append(tuple([p["latitude"], p["longitude"]]))

    points_before = []
    points_selected = []
    points_after = []

    ip = 0
    for p in points:
        if ip >= start_segment:
            if ip <= end_segment:
                points_selected.append(p)
            else:
                points_after.append(p)
        else:
            points_before.append(p)

        ip += 1

    # add lines and markers
    if len(points_selected) > 0:
        folium.PolyLine(
            points_selected,
            color=primary_color,
            weight=2.5,
            opacity=1
            ).add_to(my_map)
        add_markers(
            my_map,
            points_selected,
            primary_color,
            len(points_before)
            )
    if len(points_before) > 0:
        folium.PolyLine(
            points_before,
            color=settings.NOT_SELECTED_COLOR,
            weight=2.5,
            opacity=1
            ).add_to(my_map)
        add_markers(
            my_map,
            points_before,
            settings.NOT_SELECTED_COLOR,
            0
            )
    if len(points_after) > 0:
        folium.PolyLine(
            points_after,
            color=settings.NOT_SELECTED_COLOR,
            weight=2.5,
            opacity=1
            ).add_to(my_map)
        add_markers(
            my_map,
            points_after,
            settings.NOT_SELECTED_COLOR,
            (len(points_before) - 1 + len(points_selected))
            )

    # start marker
    if start_segment > 0:
        strStart = "Start segment "
    else:
        strStart = "Start "

    tooltip_text = strStart + atrack.displayfilename
    tooltip_style = "'color: " + primary_color + "; font-size: 0.85vw'"
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<p style='color: " + primary_color + "; font-weight: bold; font-size: 1.0vw'>" +
        strStart + atrack.displayfilename + "</p>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[start_segment],
        icon=folium.Icon(color=start_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    # finish marker
    if end_segment < len(allpoints) - 1:
        strFinish = "Finish selection "
    else:
        strFinish = "Finish "

    tooltip_text = strFinish + atrack.displayfilename
    tooltip_style = "'color: " + primary_color + "; font-size: 0.85vw'"
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<p style='color: " + primary_color + "; font-weight: bold; font-size: 1.0vw'>" +
        strFinish + atrack.displayfilename + "</p>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[end_segment],
        icon=folium.Icon(color=end_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    return my_map


def add_markers(my_map, points, marker_color, ip_start):

    ip = ip_start
    for p in points:
        tooltip_text = 'Point ' + str(ip)
        tooltip_style = 'color: maroon; font-size: 0.85vw'
        tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
        html = (
            "<p style='color: " + marker_color + "; font-weight: bold; font-size: 1.0vw'>" +
            tooltip_text + "</p>"
        )
        popup = folium.Popup(html, max_width=300)
        folium.vector_layers.CircleMarker(
                location=[p[0], p[1]],
                radius=7,
                color=marker_color,
                weight=0,
                fill_color=marker_color,
                fill_opacity=1,
                tooltip=tooltip,
                popup=popup,
            ).add_to(my_map)

        ip += 1

    return


def calculate_using_haversine(point, previous_point):
    distance = float(0.00)

    if previous_point:
        previous_location = (previous_point[0], previous_point[1])
        current_location = (point[0], point[1])
        distance = haversine(current_location, previous_location, unit='m')

    return distance
