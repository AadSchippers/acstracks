from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import HttpResponseRedirect
from django import forms
import xml.etree.ElementTree as ET
from .models import Track, Preference
from .forms import PreferenceForm
import os
from dateutil.parser import parse
from decimal import *
from datetime import datetime
import time
from .mapviews import *
import re


@login_required(login_url='/login/')
def track_list(request, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if not order_selected:
        order_selected = "created_date_ascending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    if request.method == 'POST':
        files = request.FILES.getlist('gpxfile')
        for file in files:
            fs = FileSystemStorage()
            storagefilename = fs.save(file.name, file)
            parse_file(request, storagefilename, file.name, intermediate_points_selected)
    
        order_selected = request.POST.get('Order')
        
        profile_filter = request.POST.get('Profile')

    bike_profiles = get_bike_profiles(request)
    
    tracks = get_tracks(request, order_selected, profile_filter)

    statistics = compute_statistics(tracks)

    preference = Preference.objects.get(user=request.user)

    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks,
        'preference': preference,
        'bike_profiles': bike_profiles,
        'profile_filter': profile_filter,
        'order_selected': order_selected,
        'statistics': statistics,
        'intermediate_points_selected': intermediate_points_selected,
        }
    )


def get_tracks(request, order_selected, profile_filter):
    if order_selected == "created_date_ascending":
        order_by = "created_date"
    
    if order_selected == "created_date_descending":
        order_by = "-created_date"
    
    if order_selected == "length_ascending":
        order_by = "length"
    
    if order_selected == "length_descending":
        order_by = "-length"
    
    if order_selected == "duration_ascending":
        order_by = "timelength"
    
    if order_selected == "duration_descending":
        order_by = "-timelength"
    
    if order_selected == "avgspeed_ascending":
        order_by = "avgspeed"
    
    if order_selected == "avgspeed_descending":
        order_by = "-avgspeed"
    
    if order_selected == "maxspeed_ascending":
        order_by = "maxspeed"
    
    if order_selected == "maxspeed_descending":
        order_by = "-maxspeed"
    
    if profile_filter != "All":
        tracks = Track.objects.filter(
            user=request.user,
            profile=profile_filter
            ).order_by(order_by)
    else:
        tracks = Track.objects.filter(user=request.user).order_by(order_by)

    return tracks


@login_required(login_url='/login/')
def track_detail(request, pk, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if not order_selected:
        order_selected = "created_date_ascending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    atrack = Track.objects.get(id=pk)

    csvsave = None

    if request.method == 'POST':
        intermediate_points_selected = request.POST.get('Intermediate_points')

        name = request.POST.get('name_input')
        if is_input_valid(name):
            atrack.name = name
            atrack.save()

        profile = request.POST.get('profile_input')
        if is_input_valid(profile):
            atrack.profile = profile
            atrack.save()

        csvsave = request.POST.get('csvsave')

    if csvsave == 'True':
        return process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, atrack, False, True)
    elif atrack.length == 0:
        process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, atrack, True, False)
    else:
        process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, None, True, False)
    
    map_filename = (
        "/static/maps/" +
        os.path.splitext(atrack.storagefilename)[0]+".html"
    )
    bike_profiles = get_bike_profiles(request)

    return render(request, 'acstracks_app/track_detail.html', {
        'atrack': atrack,
        'map_filename': map_filename,
        'profile_filter': profile_filter,
        'order_selected': order_selected,
        'intermediate_points_selected': int(intermediate_points_selected),     
        'bike_profiles': bike_profiles,
        }
    )


def parse_file(request, storagefilename=None, displayfilename=None, intermediate_points_selected=0):
    try:
        path = os.path.join(
            settings.MEDIA_ROOT,
            storagefilename
        )
        gpxfile = ET.parse(path)
    except Exception:
        print("Problem with " + storagefilename)
        return

    namespace = settings.NAMESPACE
    gpxroot = gpxfile.getroot()
    creator = gpxroot.attrib['creator']
    gpxtrk = gpxroot.find('ns:trk', namespace)
    name = gpxtrk.find('ns:name', namespace).text
    extensions = gpxtrk.find('ns:extensions', namespace)
    if extensions:
        created_date = extensions.find('ns:time', namespace).text
        profile = extensions.find('ns:profile', namespace).text
        # ivm met naamwijziging
        if profile == "Vakantiefiet":
            profile = "Toerfiets"
    else:
        created_date = "00:00:00"
        profile = "Fiets"

    try:
        trk = Track.objects.create(
            user=request.user,
            displayfilename=displayfilename,
            storagefilename=storagefilename,
            creator=creator,
            created_date=parse(created_date),
            name=name,
            profile=profile,
        )
        trk.save()

        process_gpx_file(request, trk.storagefilename, intermediate_points_selected, trk, False)
    except:
        pass

    return


def get_bike_profiles(request):
    dictbike_profiles = Track.objects.values('profile').distinct().filter(user=request.user)

    listbike_profiles = ['All']
    for p in dictbike_profiles:
        listbike_profiles.append(p.get('profile'))

    return listbike_profiles


def compute_statistics(tracks):
    statistics = {}

    total_length = float(0)
    total_avgspeed = float(0)
    highest_avgspeed = 0
    highest_maxspeed = 0
    longest_length = float(0)
    longest_duration = '00:00:00'
    max_ascent = float(0)
    max_descent = float(0)
    datetime_highest_avgspeed = datetime.now()
    datetime_highest_maxspeed = datetime.now()
    datetime_longest_length = datetime.now()
    datetime_longest_duration = datetime.now()
    datetime_max_ascent = datetime.now()
    datetime_max_descent = datetime.now()

    for t in tracks:
        total_length = total_length + float(t.length)
        total_avgspeed = total_avgspeed + float(t.avgspeed * t.length)
        if longest_length < t.length:
            longest_length = t.length
            datetime_longest_length = t.created_date
        if longest_duration < str(t.timelength):
            longest_duration = str(t.timelength)
            datetime_longest_duration = t.created_date
        if highest_avgspeed < t.avgspeed:
            highest_avgspeed = t.avgspeed
            datetime_highest_avgspeed = t.created_date
        if highest_maxspeed < t.maxspeed:
            highest_maxspeed = t.maxspeed
            datetime_highest_maxspeed = t.created_date
        if max_descent < t.totaldescent:
            max_descent = t.totaldescent
            datetime_max_descent = t.created_date
        if max_ascent < t.totalascent:
            max_ascent = t.totalascent
            datetime_max_ascent = t.created_date

    if total_length > 0:
        total_avgspeed = round((total_avgspeed / total_length), 2)

    total_length = round((total_length), 2)
            
    statistics = {
        'total_length': total_length,
        'total_avgspeed': total_avgspeed,
        'highest_avgspeed': highest_avgspeed,
        'highest_maxspeed': highest_maxspeed,
        'longest_length': longest_length,
        'longest_duration': longest_duration,
        'max_ascent': max_ascent,
        'max_descent': max_descent,
        'datetime_highest_avgspeed': datetime_highest_avgspeed,
        'datetime_highest_maxspeed': datetime_highest_maxspeed,
        'datetime_longest_length': datetime_longest_length,
        'datetime_longest_duration': datetime_longest_duration,
        'datetime_max_ascent': datetime_max_ascent,
        'datetime_max_descent': datetime_max_descent,
    }

    return statistics


def is_input_valid(input=None):
    pattern = (r"^[A-z0-9\- \ ]+$")
    try:
        return re.match(pattern, input) is not None
    except:
        return None


def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')
    # Redirect to a success page.


@login_required(login_url='/login/')
def process_preferences(request):
    form = PreferenceForm()
    if request.method == "POST":
        form = PreferenceForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            speedthreshold = data['speedthreshold']
            elevationthreshold = data['elevationthreshold']
            show_avgspeed = data['show_avgspeed']
            show_maxspeed = data['show_maxspeed']
            show_totalascent = data['show_totalascent']
            show_totaldescent = data['show_totaldescent']
            show_avgcadence = data['show_avgcadence']
            show_avgheartrate = data['show_avgheartrate']

            try:
                preference = Preference.objects.get(user=request.user)
                preference.speedthreshold = speedthreshold
                preference.elevationthreshold = elevationthreshold
                preference.show_avgspeed = show_avgspeed
                preference.show_maxspeed = show_maxspeed
                preference.show_totalascent = show_totalascent
                preference.show_totaldescent = show_totaldescent
                preference.show_avgcadence = show_avgcadence
                preference.show_avgheartrate = show_avgheartrate
                preference.save()
            except:
                preference = Preference.objects.create(
                    user=request.user,
                    speedthreshold=speedthreshold,
                    elevationthreshold=elevationthreshold
                )

            recalculate_tracks(request)
            return redirect('track_list')
    else:
        try:
            preference = Preference.objects.get(user=request.user)
            form = PreferenceForm(initial={
                'speedthreshold': preference.speedthreshold,
                'elevationthreshold': preference.elevationthreshold,
                'show_avgspeed': preference.show_avgspeed,
                'show_maxspeed': preference.show_maxspeed,
                'show_totalascent': preference.show_totalascent,
                'show_totaldescent': preference.show_totaldescent,
                'show_avgcadence': preference.show_avgcadence,
                'show_avgheartrate': preference.show_avgheartrate,
            })
        except:
            form = PreferenceForm()

    return render(request, 'acstracks_app/preference_form.html', {'form': form})


def recalculate_tracks(request):
    tracks = Track.objects.filter(user=request.user)
    for track in tracks:
        process_gpx_file(request, track.storagefilename, 0, track, False)

    return
