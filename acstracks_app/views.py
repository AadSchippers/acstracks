from django.shortcuts import render, redirect
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import xml.etree.ElementTree as ET
from .models import Track, Trkpt
import os
from dateutil.parser import parse
from decimal import *
from datetime import datetime
import time


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
                profile=profile_filter
                ).order_by('created_date')
        else:
            tracks = Track.objects.all().order_by('created_date')
    else:
        profile_filter = "All"
        tracks = Track.objects.all().order_by('created_date')

    statistics = compute_statistics(tracks)
    
    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks,
        'profiles': profiles,
        'profile_filter': profile_filter,
        'statistics': statistics
        }
    )


def track_detail(request, pk):
    atrack = Track.objects.get(id=pk)

    trkpts = Trkpt.objects.filter(trackid=atrack)
    
    return render(request, 'acstracks_app/track_detail.html', {
        'atrack': atrack,
        'trkpts': trkpts,
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
            filename=filename,
            creator=creator,
            created_date=parse(created_date),
            name=name,
            profile=profile,
            length=Decimal(trkLength),
            timelength=trkTimelength,
            avgspeed=Decimal(trkAvgspeed),
            maxspeed=Decimal(trkMaxspeed),
            avgcadence=trkAvgcadence,
            maxcadence=trkMaxcadence,
            avgheartrate=trkAvgheartrate,
            minheartrate=trkMinheartrate,
            maxheartrate=trkMaxheartrate,
        )
        trk.save()
        '''
        Too time consuming
        get_trkpts(trk, gpxfile)
        '''
    except:
        pass

    return


def get_trkpts(trk, gpxfile):
    namespace = settings.NAMESPACE
    gpxroot = gpxfile.getroot()
    gpxtrk = gpxroot.find('ns:trk', namespace)
    for gpxtrkseg in gpxtrk.findall('ns:trkseg', namespace):
        for trkpt in gpxtrkseg.findall('ns:trkpt', namespace):
            lat = trkpt.get('lat')
            lon = trkpt.get('lon')
            ele = trkpt.find('ns:ele', namespace).text
            time = trkpt.find('ns:time', namespace).text
            extensions = trkpt.find('ns:extensions', namespace)
            distance = extensions.find('ns:distance', namespace).text
            speed = extensions.find('ns:speed', namespace).text
            cadence = extensions.find('ns:cadence', namespace)
            heartrate = extensions.find('ns:heartrate', namespace)
        
            trkDistance = float(distance) / 1000
            trkSpeed = float(speed) * 3.6

            try:
                trkCadence = int(cadence.text)
            except:
                trkCadence = None
            try:
                trkHeartrate = int(heartrate.text)
            except:
                trkHeartrate = None

            #try:
            atrkpt = Trkpt.objects.create(
                trackid=trk,
                lat=Decimal(lat),
                lon=Decimal(lon),
                ele=Decimal(ele),
                time=parse(time),
                distance=Decimal(trkDistance),
                speed=Decimal(trkSpeed),
                cadence=trkCadence,
                heartrate=trkHeartrate,
            )
            atrkpt.save()
            #except:
            #    pass

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
    longest_length = float(0)
    longest_duration = '00:00:00'
    datetime_highest_avgspeed = datetime.now()
    datetime_highest_maxspeed = datetime.now()
    datetime_longest_length = datetime.now()
    datetime_longest_duration = datetime.now()

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
        'datetime_highest_avgspeed': datetime_highest_avgspeed,
        'datetime_highest_maxspeed': datetime_highest_maxspeed,
        'datetime_longest_length': datetime_longest_length,
        'datetime_longest_duration': datetime_longest_duration,
    }

    return statistics
