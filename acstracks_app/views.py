from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import xml.etree.ElementTree as ET
from .models import Track
import os
from dateutil.parser import parse
from decimal import *
from datetime import datetime


def track_list(request):
    profile_filter = None
    if request.method == 'POST':
        files = request.FILES.getlist('myfile')
        for file in files:
            fs = FileSystemStorage()
            storagefilename = fs.save(file.name, file)
            parse_file(storagefilename, file.name)
        
        profile_filter = request.POST.get('Profile')

    profiles = get_profiles()

    if profile_filter:
        if profile_filter != "All":
            tracks = Track.objects.filter(
                profile=profile_filter).order_by('created_date'
            )
        else:
            tracks = Track.objects.all().order_by('created_date')
    else:
        tracks = Track.objects.all().order_by('created_date')

    statistics = compute_statistics(tracks)
    
    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks, 
        'profiles': profiles, 
        'statistics': statistics
        }
    )


def parse_file(storagefilename=None, filename=None):
    try:
        path = os.path.join(
            settings.MEDIA_ROOT,
            storagefilename
        )
        gpxfile = ET.parse(path)
    except Exception:
        print("Problem with " + storagefilename)

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
    avgspeed = extensions.find('ns:avgspeed', namespace).text
    maxspeed = extensions.find('ns:maxspeed', namespace).text
    avgcadence = extensions.find('ns:avgcadence', namespace)
    maxcadence = extensions.find('ns:maxcadence', namespace)
    avgheartrate = extensions.find('ns:avgheartrate', namespace)
    minheartrate = extensions.find('ns:minheartrate', namespace)
    maxheartrate = extensions.find('ns:maxheartrate', namespace)

    trkLength = float(length) / 1000
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
            filename=filename,
            creator=creator,
            created_date=parse(created_date),
            name=name,
            profile=profile,
            length=Decimal(trkLength),
            avgspeed=Decimal(trkAvgspeed),
            maxspeed=Decimal(trkMaxspeed),
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


def get_profiles():
    dictProfiles = Track.objects.values('profile').distinct()

    listProfiles = ['All']
    for p in dictProfiles:
        listProfiles.append(p.get('profile'))

    return listProfiles


def compute_statistics(tracks):
    statistics = {}

    #getcontext().prec = 2

    total_length = float(0)
    total_avgspeed = float(0)
    highest_avgspeed = 0
    highest_maxspeed = 0
    datetime_highest_avgspeed = datetime.now()
    datetime_highest_maxspeed = datetime.now()

    for t in tracks:
        total_length = total_length + float(t.length)
        total_avgspeed = total_avgspeed + float(t.avgspeed * t.length)
        if highest_avgspeed < t.avgspeed:
            highest_avgspeed = t.avgspeed
            datetime_highest_avgspeed = t.created_date
        if highest_maxspeed < t.maxspeed:
            highest_maxspeed = t.maxspeed
            datetime_highest_maxspeed = t.created_date

    if total_length > 0:
        total_avgspeed = round((total_avgspeed / total_length), 2)

    total_length = round((total_length), 2)
            
    statistics = {
        'total_length': total_length,
        'total_avgspeed': total_avgspeed,
        'highest_avgspeed': highest_avgspeed,
        'highest_maxspeed': highest_maxspeed,
        'datetime_highest_avgspeed': datetime_highest_avgspeed,
        'datetime_highest_maxspeed': datetime_highest_maxspeed,
    }

    return statistics
