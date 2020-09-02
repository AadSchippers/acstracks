from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import HttpResponseRedirect
import xml.etree.ElementTree as ET
from .models import Track
import os
from dateutil.parser import parse
from decimal import *
from datetime import datetime
import time
from .mapviews import *


@login_required(login_url='/login/')
def track_list(request, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if request.method == 'POST':
        files = request.FILES.getlist('myfile')
        for file in files:
            fs = FileSystemStorage()
            storagefilename = fs.save(file.name, file)
            parse_file(request, storagefilename, file.name)
    
        order_selected = request.POST.get('Order')
        
        profile_filter = request.POST.get('Profile')

    if not order_selected:
        order_selected = "created_date_ascending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    bike_profiles = get_bike_profiles()
    
    tracks = get_tracks(request, order_selected, profile_filter)

    statistics = compute_statistics(tracks)
    
    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks,
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
        order_by = "-avgspeed"
    
    if order_selected == "avgspeed_descending":
        order_by = "-avgspeed"
    
    if order_selected == "maxspeed_ascending":
        order_by = "maxspeed"
    
    if order_selected == "maxspeed_descending":
        order_by = "-maxspeed"
    
    if profile_filter != "All":
        tracks = Track.objects.filter(
            username=request.user.username,
            profile=profile_filter
            ).order_by(order_by)
    else:
        tracks = Track.objects.filter(username=request.user.username).order_by(order_by)

    return tracks


@login_required(login_url='/login/')
def track_detail(request, pk, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if request.method == 'POST':       
        intermediate_points_selected = request.POST.get('Intermediate_points')

    if not order_selected:
        order_selected = "created_date_ascending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    atrack = Track.objects.get(id=pk)

    process_gpx_file(atrack.storagefilename, intermediate_points_selected)
    
    return render(request, 'acstracks_app/track_detail.html', {
        'atrack': atrack,
        'profile_filter': profile_filter,
        'order_selected': order_selected,
        'intermediate_points_selected': int(intermediate_points_selected),     
        }
    )


def parse_file(request, storagefilename=None, displayfilename=None):
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
    created_date = extensions.find('ns:time', namespace).text
    profile = extensions.find('ns:profile', namespace).text
    # ivm met naamwijziging
    if profile == "Vakantiefiet":
        profile = "Toerfiets"
    length = extensions.find('ns:length', namespace).text
    timelength = extensions.find('ns:timelength', namespace).text
    avgspeed = extensions.find('ns:avgspeed', namespace).text
    maxspeed = extensions.find('ns:maxspeed', namespace).text
    totalascent = extensions.find('ns:totalascent', namespace).text
    totaldescent = extensions.find('ns:totaldescent', namespace).text
    avgcadence = extensions.find('ns:avgcadence', namespace)
    maxcadence = extensions.find('ns:maxcadence', namespace)
    avgheartrate = extensions.find('ns:avgheartrate', namespace)
    minheartrate = extensions.find('ns:minheartrate', namespace)
    maxheartrate = extensions.find('ns:maxheartrate', namespace)

    trkLength = float(length) / 1000
    trkTimelength = time.strftime('%H:%M:%S', time.gmtime(int(timelength)))
    trkAvgspeed = float(avgspeed) * 3.6
    trkMaxspeed = float(maxspeed) * 3.6
    try:
        trkAvgcadence = int(avgcadence.text)
    except:
        trkAvgcadence = None
    try:
        trkMaxcadence = int(maxcadence.text)
    except:
        trkMaxcadence = None
    try:
        trkAvgheartrate = int(avgheartrate.text)
    except:
        trkAvgheartrate = None
    try:
        trkMinheartrate = int(minheartrate.text)
    except:
        trkMinheartrate = None
    try:
        trkMaxheartrate = int(maxheartrate.text)
    except:
        trkMaxheartrate = None

    getcontext().prec = 2

    try:
        trk = Track.objects.create(
            username=request.user.username,
            displayfilename=displayfilename,
            storagefilename=storagefilename,
            creator=creator,
            created_date=parse(created_date),
            name=name,
            profile=profile,
            length=Decimal(trkLength),
            timelength=trkTimelength,
            avgspeed=Decimal(trkAvgspeed),
            maxspeed=Decimal(trkMaxspeed),
            totalascent=Decimal(totalascent),
            totaldescent=Decimal(totaldescent),
            avgcadence=trkAvgcadence,
            maxcadence=trkMaxcadence,
            avgheartrate=trkAvgheartrate,
            minheartrate=trkMinheartrate,
            maxheartrate=trkMaxheartrate,
        )
        trk.save()
    except:
        pass

    return


def get_bike_profiles():
    dictbike_profiles = Track.objects.values('profile').distinct()

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


def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')
    # Redirect to a success page.