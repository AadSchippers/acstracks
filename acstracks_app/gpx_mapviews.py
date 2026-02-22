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
import csv
from django.http import HttpResponse
import io
import copy


def process_gpx_file(request, file):
    try:
        atrack = {
            "filename": file.name,
            "distance": 0,
            "reversed": False
        }
        reader = io.BufferedReader(file.file)
        wrapper = io.TextIOWrapper(reader)
        gpx_file = wrapper.read()

        gpx = gpxpy.parse(gpx_file)

        points = []
        timezone_info = timezone(settings.TIME_ZONE)
        previous_point = None
        distance = 0
        trackname = ""
        for track in gpx.tracks:
            trackname = track.name
            for segment in track.segments:
                for point in segment.points:

                    points.append(tuple([
                        point.latitude,
                        point.longitude,
                        point.elevation,
                        ]))

                    point_distance = calculate_using_haversine(
                        points[len(points)-1], previous_point
                        )
                    distance += point_distance

                    previous_point = points[len(points)-1]

            atrack["trackname"] = trackname
            atrack["distance"] = round(distance/1000, 2)
            atrack["points"] = points
    except Exception:
        atrack = None

    return atrack


def order_tracks(request, original_tracks):
    tracks = copy.deepcopy(original_tracks)
    number_of_tracks = len(tracks)
    ordered_tracks = []
    ordered_tracks.append(tracks.pop(0))

    while len(ordered_tracks) < number_of_tracks:
        i = 0
        last_track = ordered_tracks[len(ordered_tracks)-1]
        previous_point = last_track["points"][len(last_track["points"])-1]
        point_distance = 9999999999
        ti = 0
        for t in tracks:
            if t["reversed"] == True:
                t["points"].reverse()
                t["reversed"] = False
            point_first = t["points"][0]
            point_last = t["points"][len(t["points"])-1]
            point_distance_first = calculate_using_haversine(
                point_first, previous_point
                )
            point_distance_last = calculate_using_haversine(
                point_last, previous_point
                )
            if point_distance_last < point_distance_first:
                if point_distance_last < point_distance:
                    t["points"].reverse()
                    t["reversed"] = True
                    point_distance = point_distance_last
                    tpop = ti
            elif point_distance_first < point_distance:
                t["reversed"] = False
                point_distance = point_distance_first
                tpop = ti

            ti += 1
        ordered_tracks.append(tracks.pop(tpop))

        i += 1

    return ordered_tracks


def make_map(
    request, colorscheme, tracks, map_filename, start_selection, end_selection, split_track, set_new_start_point
):

    ave_lats = []
    ave_lons = []
    for t in tracks:
        ave_lats.append(sum(float(p[0]) for p in t["points"])/len(t["points"]))
        ave_lons.append(sum(float(p[1]) for p in t["points"])/len(t["points"]))

    ave_lat = sum(float(p) for p in ave_lats) / len(ave_lats)
    ave_lon = sum(float(p) for p in ave_lons) / len(ave_lons)

    # Load map centred on average coordinates
    my_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)

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

    # add lines
    folium.PolyLine(
        points,
        color=settings.CONNECT_COLOR,
        weight=2.5,
        opacity=1
        ).add_to(my_map)

    gpx_primary_color = settings.PRIMARY_COLOR[colorscheme]
    gpx_start_color = settings.START_COLOR[colorscheme]
    gpx_end_color = settings.END_COLOR[colorscheme]

    if len(tracks) > 1:
        i = 0
        for track in tracks:
            if i > 0:
                gpx_start_color = settings.PRIMARY_COLOR[colorscheme]
            if i < (len(tracks) - 1):
                gpx_end_color = settings.PRIMARY_COLOR[colorscheme]
            my_map = draw_map(
                request,
                my_map,
                track,
                gpx_primary_color,
                gpx_start_color,
                gpx_end_color,
                start_selection,
                end_selection,
                False,
                False
                )
            i += 1
    else:
        my_map = draw_map(
            request,
            my_map,
            track,
            gpx_primary_color,
            gpx_start_color,
            gpx_end_color,
            start_selection,
            end_selection,
            split_track,
            set_new_start_point
            )

    folium.LayerControl(collapsed=True).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.GPX_MAPS_ROOT,
            map_filename
        )
    my_map.save(mapfilename)

    return


def draw_map(
    request, my_map, track, gpx_primary_color, gpx_start_color, gpx_end_color,
    start_selection, end_selection, split_track, set_new_start_point
):
    if end_selection > len(track["points"]) - 1:
        end_selection = len(track["points"]) - 1

    points = []
    for p in track["points"]:
        points.append(tuple([p[0], p[1]]))

    points_before = []
    points_selected = []
    points_after = []
    if split_track == 'on' or set_new_start_point == 'on':
        ip = 0
        for p in points:
            if ip >= start_selection:
                if ip <= end_selection:
                    points_selected.append(p)
                else:
                    points_after.append(p)
            else:
                points_before.append(p)

            ip += 1

    # add lines and markers
    if split_track  == 'on' or set_new_start_point == 'on':
        if len(points_selected) > 0:
            folium.PolyLine(
                points_selected,
                color=gpx_primary_color,
                weight=2.5,
                opacity=1
                ).add_to(my_map)
            add_markers(
                my_map,
                points_selected,
                gpx_primary_color,
                gpx_primary_color,
                len(points_before)
                )
        if len(points_before) > 0:
            folium.PolyLine(
                points_before,
                gpx_primary_color,
                color=settings.NOT_SELECTED_COLOR,
                weight=2.5,
                opacity=1
                ).add_to(my_map)
            add_markers(
                my_map,
                points_before,
                gpx_primary_color,
                settings.NOT_SELECTED_COLOR,
                0
                )
        if len(points_after) > 0:
            folium.PolyLine(
                points_after,
                gpx_primary_color,
                color=settings.NOT_SELECTED_COLOR,
                weight=2.5,
                opacity=1
                ).add_to(my_map)
            add_markers(
                my_map,
                points_after,
                gpx_primary_color,
                settings.NOT_SELECTED_COLOR,
                (len(points_before) - 1 + len(points_selected))
                )
    else:
        folium.PolyLine(
            points,
            color=gpx_primary_color,
            weight=2.5,
            opacity=1
            ).add_to(my_map)

    # start marker
    if not split_track == 'on':
        start_selection = 0

    if start_selection > 0:
        strStart = "Start selection "
    else:
        strStart = "Start "

    tooltip_text = strStart + track["filename"]
    tooltip_style = 'color: ' + gpx_primary_color + '; font-size: 0.85vw'
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<p style='color: " + gpx_primary_color + "; font-weight: bold; font-size: 1.0vw'>" +
        strStart + track["filename"] + "</p>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[start_selection],
        icon=folium.Icon(color=gpx_start_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    # finish marker
    if not split_track == 'on':
        end_selection = len(track["points"]) - 1

    if end_selection < len(track["points"]) - 1:
        strFinish = "Finish selection "
    else:
        strFinish = "Finish "

    tooltip_text = strFinish + track["filename"]
    tooltip_style = 'color: ' + gpx_primary_color + '; font-size: 0.85vw'
    tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
    html = (
        "<p style='color: " + gpx_primary_color + "; font-weight: bold; font-size: 1.0vw'>" +
        strFinish + track["filename"] + "</p>"
    )
    popup = folium.Popup(html, max_width=300)
    folium.Marker(
        points[end_selection],
        icon=folium.Icon(color=gpx_end_color),
        tooltip=tooltip,
        popup=popup
        ).add_to(my_map)

    return my_map


def add_markers(my_map, points, gpx_primary_color, gpx_marker_color, ip_start):

    ip = ip_start
    for p in points:
        tooltip_text = 'Point ' + str(ip)
        tooltip_style = 'color: ' + gpx_primary_color + '; font-size: 0.85vw'
        tooltip = folium.Tooltip(tooltip_text, style=tooltip_style)
        html = (
            "<p style='color: " + gpx_primary_color + "; font-weight: bold; font-size: 1.0vw'>" +
            tooltip_text + "</p>"
        )
        popup = folium.Popup(html, max_width=300)
        folium.vector_layers.CircleMarker(
                location=[p[0], p[1]],
                radius=7,
                color=gpx_marker_color,
                weight=0,
                fill_color=gpx_marker_color,
                fill_opacity=1,
                tooltip=tooltip,
                popup=popup,
            ).add_to(my_map)

        ip += 1

    return


def download_gpx(request, trackname, tracks, start_selection, end_selection):
    # Create the HttpResponse object with the appropriate header.
    response = HttpResponse(content_type='text/gpx')
    if not trackname:
        trackname = tracks[0]["trackname"]
    response['Content-Disposition'] = (
        'attachment; filename="' +
        trackname +
        '.gpx"'
        )

    writer = csv.writer(response)

    writer.writerow([str("<?xml version='1.0' encoding='UTF-8'?>")])

    writer.writerow([
        str("<gpx version='1.1' creator='acsgpxstitch' " +
            "xmlns='http://www.topografix.com/GPX/1/1' " +
            "xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' " +
            "xsi:schemaLocation='http://www.topografix.com/GPX/1/1 " +
            "http://www.topografix.com/GPX/1/1/gpx.xsd'>")
        ])
    writer.writerow([str("  <trk>")])
    writer.writerow([str("    <name>"+escaped(trackname)+"</name>")])

    for t in tracks:
        writer.writerow([str("    <trkseg>")])
        points = t["points"]
        row = 0
        while row < len(points):
            if row >= start_selection:
                if row <= end_selection:
                    writer.writerow([
                            str("      <trkpt lat='" +
                                str(points[row][0]) +
                                "' lon='"+str(points[row][1])+"'>")
                        ])
                    writer.writerow([
                        str("        <ele>"+str(points[row][2])+"</ele>")
                        ])
                    writer.writerow([str("      </trkpt>")])
            row += 1

        writer.writerow([str("    </trkseg>")])

    writer.writerow([str("  </trk>")])
    writer.writerow([str("</gpx>")])

    return response


def calculate_using_haversine(point, previous_point):
    distance = float(0.00)

    if previous_point:
        previous_location = (previous_point[0], previous_point[1])
        current_location = (point[0], point[1])
        distance = haversine(current_location, previous_location, unit='m')

    return distance


def escaped(astring):
    astring = astring.replace("&", "&amp;")
    astring = astring.replace("<", "&lt;")
    astring = astring.replace(">", "&gt;")
    astring = astring.replace("'", "&apos;")
    astring = astring.replace('"', "&quot;")

    return astring
