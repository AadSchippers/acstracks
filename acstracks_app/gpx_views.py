from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.messages import get_messages
from django.shortcuts import HttpResponseRedirect
from django import forms
import xml.etree.ElementTree as ET
import os
from dateutil.parser import parse
from decimal import *
from datetime import datetime
import time
from .gpx_mapviews import *
from .models import Preference
from .views import set_backgroundimage
import re
import hashlib
import ast
import copy
import random


def track_list(request):
    try:
        preference = Preference.objects.get(user=request.user)
        colorscheme = preference.colorscheme
        primary_color =  settings.PRIMARY_COLOR[preference.colorscheme]
        backgroundimage = set_backgroundimage(preference)
    except Exception:
        colorscheme = settings.DEFAULT_GPX_COLORSCHEME
        primary_color =  settings.PRIMARY_COLOR[colorscheme]
        backgroundimage = '/static/img/acsgpxstitchbg-blurred.png'
        
    map_filename_random = "_" + str(random.randint(0, 99)).zfill(2)
    map_filename = (
        settings.GPX_TRACK_MAP.replace('.html', map_filename_random) + '.html'
        )
    basemap_filename = settings.GPX_BASE_MAP
    trackname = None
    gpxdownload = None
    intelligent_stitch = None
    split_track = None
    reverse_track = None
    new_start_point_possible = False
    set_new_start_point = None
    new_start_point = 0
    start_selection = 0
    end_selection = 9999999
    tracks = []
    original_tracks = []

    if request.method == 'POST':
        files = request.FILES.getlist('gpxfile')
        if files:
            original_tracks = []
        for file in files:
            new_track = []
            try:
                new_track = (process_gpx_file(request, file))
                if new_track:
                    original_tracks.append(copy.deepcopy(new_track))
                else:
                    # error processing file, file skipped
                    messages.error(
                        request,
                        "Error processing " +
                        file.name +
                        ", file skipped.")
            except Exception:
                pass

        gpxdownload = request.POST.get('gpxdownload')
        if not original_tracks:
            try:
                original_tracks = ast.literal_eval(
                    request.POST.get('original_tracks')
                    )
            except Exception:
                return redirect('track_list')

        if len(original_tracks) == 0:
            return redirect('track_list')

        original_tracks = sorted(original_tracks, key=lambda d: d['filename']) 
        tracks = original_tracks.copy()

        if len(original_tracks) == 1:
            new_start_point_possible = calculate_using_haversine(
                    tracks[0]["points"][0],
                    tracks[0]["points"][len(tracks[0]["points"])-1],
                ) < 100

            reverse_track = request.POST.get('reverse_track')
            split_track = request.POST.get('split_track')
            try:
                start_selection = int(request.POST.get('start_selection'))
            except Exception:
                pass
            try:
                end_selection = int(request.POST.get('end_selection'))
            except Exception:
                pass
            try:
                if start_selection > end_selection:
                    start_selection, end_selection = end_selection, start_selection
            except:
                pass

            set_new_start_point = request.POST.get('set_new_start_point')
            try:
                new_start_point = int(request.POST.get('new_start_point'))
            except Exception:
                pass
            if new_start_point > 0:
                points = tracks[0]["points"]
                tracks[0]["points"] = compute_new_start_point(new_start_point, points)
            intelligent_stitch = None
            if reverse_track == 'on':
                if tracks[0]["reversed"] == False: 
                    tracks[0]["reversed"] = True
                    tracks[0]["points"].reverse()
            else:
                if tracks[0]["reversed"] == True: 
                    tracks[0]["reversed"] = False
                    tracks[0]["points"].reverse()
        else:
            split_track = None
            reverse_track = None
            intelligent_stitch = request.POST.get('intelligent_stitch')
            if intelligent_stitch:
                tracks = order_tracks(request, original_tracks)

        if gpxdownload == 'True':
            trackname = request.POST.get('trackname')
            if trackname:
                if not is_input_valid(trackname):
                    # invalid characters in input have been skipped
                    messages.error(
                        request,
                        "Invalid characters in track name."
                    )
                    gpxdownload = False

        if gpxdownload == 'True':
            return download_gpx(
                request, trackname, tracks, start_selection, end_selection
                )

        make_map(
            request,
            colorscheme,
            tracks,
            map_filename,
            start_selection,
            end_selection,
            split_track,
            set_new_start_point,
            )

    total_distance = 0
    for t in tracks:
        total_distance += t["distance"]

    return render(request, 'acsgpxstitch_app/track_list.html', {
        'colorscheme': colorscheme,
        'primary_color': primary_color,
        'backgroundimage': backgroundimage,
        "tracks": tracks,
        "original_tracks": original_tracks,
        "intelligent_stitch": intelligent_stitch,
        "split_track": split_track,
        "start_selection": start_selection,
        "end_selection": end_selection,
        "reverse_track": reverse_track,
        "new_start_point_possible": new_start_point_possible,
        "set_new_start_point": set_new_start_point,
        "new_start_point": new_start_point,
        "total_distance": round(total_distance, 2),
        "map_filename": "/static/maps/" + map_filename,
        "basemap_filename": "/static/maps/" + basemap_filename,
        "trackname": trackname,
        'page_name': "AcsGPXStitch",

        }
    )


def compute_new_start_point(new_start_point, points):
    new_points = []
    for ip, p in enumerate(points):
        if ip >= new_start_point:
            new_points.append(p)
    for ip, p in enumerate(points):
        if ip < new_start_point:
            new_points.append(p)

    return new_points

def is_input_valid(input=None):
    pattern = (r"^[A-z0-9\- +\ ]+$")
    try:
        return re.match(pattern, input) is not None
    except Exception:
        return None
