from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timezone import make_aware
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required, user_passes_test
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
import hashlib
import ast


@login_required(login_url='/login/')
def track_list(request, date_start=None, date_end=None, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if not order_selected:
        order_selected = "created_date_descending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0
 
    if request.method == 'POST':
        files = request.FILES.getlist('gpxfile')
        for file in files:
            storagefilename = (
                request.user.username +
                '-' +
                file.name
             )
            fs = FileSystemStorage()
            try:
                fs.delete(storagefilename)
            except:
                pass
            storagefilename = fs.save(storagefilename, file)
            parse_file(request, storagefilename, file.name)
    
        if files:
            date_start = None
            date_end = None
            order_selected = None
            profile_filter = None
        else:
            date_start = request.POST.get('Date_start')
            date_end = request.POST.get('Date_end')
            order_selected = request.POST.get('Order')
            profile_filter = request.POST.get('Profile')


    if not order_selected:
        order_selected = "created_date_descending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0
 
    try:
        datetime.strptime(date_start, '%Y-%m-%d')
    except:
        date_start = get_first_date(request)
    
    try:
        datetime.strptime(date_end, '%Y-%m-%d')
    except:
        date_end = datetime.now().strftime("%Y-%m-%d")

    bike_profile_filters = get_bike_profile_filters(request)
    
    tracks = get_tracks(request, date_start, date_end, order_selected, profile_filter)

    statistics = compute_statistics(tracks)

    try:
        preference = Preference.objects.get(user=request.user)
    except:
        preference = Preference.objects.create(
            user=request.user,
        )

    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks,
        'preference': preference,
        'bike_profile_filters': bike_profile_filters,
        'date_start': date_start,
        'date_end': date_end,
        'profile_filter': profile_filter,
        'order_selected': order_selected,
        'statistics': statistics,
        'intermediate_points_selected': intermediate_points_selected,
        }
    )


def get_tracks(request, date_start, date_end, order_selected, profile_filter):
    order_by = None
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

    date_start = make_aware(parse(date_start + " 00:00:00"))
    date_end = make_aware(parse(date_end + " 23:59:59"))

    if profile_filter != "All":
        tracks1 = Track.objects.filter(
            user=request.user,
            profile__startswith=profile_filter,
            created_date__gte=date_start,
            created_date__lte=date_end,
            )
        tracks2 = Track.objects.filter(
            user=request.user,
            profile__icontains='+' + profile_filter,
            created_date__gte=date_start,
            created_date__lte=date_end,
            )
        alltracks = tracks1 | tracks2
        if order_by:
            tracks = alltracks.distinct().order_by(order_by)
        else:
            tracks = alltracks.distinct()
    else:
        if order_by:
            tracks = Track.objects.filter(
                user=request.user,
                created_date__gte=date_start,
                created_date__lte=date_end,
                ).order_by(order_by)
        else:
            tracks = Track.objects.filter(
                user=request.user,
                created_date__gte=date_start,
                created_date__lte=date_end
                )

    return tracks


def get_first_date(request):
    tracks = Track.objects.filter(
        user=request.user,
        ).order_by('created_date')

    try:
        date_start = tracks[0].created_date.strftime("%Y-%m-%d")
    except:
        date_start = datetime.now().strftime("%Y-%m-%d")

    return date_start


@login_required(login_url='/login/')
def track_detail(request, pk, date_start=None, date_end=None, order_selected=None, profile_filter=None, intermediate_points_selected=None):
    if not order_selected:
        order_selected = "created_date_ascending"
    if not profile_filter:
        profile_filter = "All"
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    try:
        atrack = Track.objects.get(id=pk, user=request.user)
    except:
        return redirect('track_list')
    
    map_filename = (
        atrack.user.username+".html"
    )
    
    full_map_filename = (
        "/static/maps/" +
        atrack.user.username+".html"
    )

    bike_profiles = get_bike_profiles(request)

    csvsave = None

    public_url = request.scheme + "://" + request.get_host() + "/publictrack/" + atrack.publickey

    if request.method == 'POST':
        intermediate_points_selected = request.POST.get('Intermediate_points')

        name = request.POST.get('name_input')
        if is_input_valid(name):
            atrack.name = name
            atrack.save()
            return render(request, 'acstracks_app/track_detail.html', {
                'atrack': atrack,
                'map_filename': full_map_filename,
                'date_start': date_start,
                'date_end': date_end,
                'order_selected': order_selected,
                'profile_filter': profile_filter,
                'intermediate_points_selected': int(intermediate_points_selected),     
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                }
            )

        profile = request.POST.get('profile_input')
        if profile == '':
            profile = '-'
        if is_input_valid(profile):
            if profile == '-':
                profile = None
            atrack.profile = profile
            atrack.save()
            return render(request, 'acstracks_app/track_detail.html', {
                'atrack': atrack,
                'map_filename': full_map_filename,
                'date_start': date_start,
                'date_end': date_end,
                'order_selected': order_selected,
                'profile_filter': profile_filter,
                'intermediate_points_selected': int(intermediate_points_selected),     
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                }
            )

        csvsave = request.POST.get('csvsave')

        confirm_delete = request.POST.get('confirm_delete')
        if confirm_delete:
            fs = FileSystemStorage()
            try:
                fs.delete(atrack.storagefilename)
            except:
                pass
            atrack.delete()

            return redirect('track_list')

    if csvsave == 'True':
        return process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, atrack, None, True, False)
    elif atrack.length == 0:
        process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, atrack, map_filename, False, False)
    else:
        process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, None, map_filename, False, False)

    return render(request, 'acstracks_app/track_detail.html', {
        'atrack': atrack,
        'map_filename': full_map_filename,
        'date_start': date_start,
        'date_end': date_end,
        'date_start': date_start,
        'date_end': date_end,
        'order_selected': order_selected,
        'profile_filter': profile_filter,
        'intermediate_points_selected': int(intermediate_points_selected),     
        'bike_profiles': bike_profiles,
        'public_url': public_url,
        }
    )


def publictrack_detail(request, publickey, intermediate_points_selected=None):
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    try:
        atrack = Track.objects.get(publickey=publickey)
    except:
        return redirect('track_list')

    map_filename = (
        atrack.user.username+"_public.html"
    )

    full_map_filename = (
        "/static/maps/" +
        atrack.user.username+"_public.html"
    )

    gpxdownload = None

    if request.method == 'POST':
        intermediate_points_selected = request.POST.get('Intermediate_points')
        gpxdownload = request.POST.get('gpxdownload')


    if gpxdownload == 'True':
        return process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, atrack, None, False, True)

    process_gpx_file(request, atrack.storagefilename, intermediate_points_selected, None, map_filename, False, False)

    return render(request, 'acstracks_app/publictrack_detail.html', {
        'atrack': atrack,
        'map_filename': full_map_filename,
        'intermediate_points_selected': int(intermediate_points_selected),
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
    metadata = gpxroot.find('ns:metadata', namespace)
    if metadata:
        created_date = metadata.find('ns:time', namespace).text
    else:
        created_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    gpxtrk = gpxroot.find('ns:trk', namespace)
    name = gpxtrk.find('ns:name', namespace).text

    extensions = gpxtrk.find('ns:extensions', namespace)
    if extensions:
        profile = extensions.find('ns:profile', namespace).text
        # ivm met naamwijziging
        if profile == "Vakantiefiet":
            profile = "Toerfiets"
    else:
        profile = None

    try:
        trk = Track.objects.create(
            user=request.user,
            displayfilename=displayfilename,
            storagefilename=storagefilename,
            creator=creator,
            created_date=parse(created_date),
            name=name,
            profile=profile,
            publickey=hashlib.sha256(storagefilename.encode()).hexdigest(),
        )
        trk.save()

        process_gpx_file(request, trk.storagefilename, intermediate_points_selected, trk, False, False, False)
    except:
        pass

    return


def get_bike_profiles(request):
    dictbike_profiles = Track.objects.values('profile').distinct().filter(user=request.user)

    listbike_profiles = ['All']
    for p in dictbike_profiles:
        try:
            listbike_profiles.append(p.get('profile').lower())
        except:
            pass

    return listbike_profiles


def get_bike_profile_filters(request):
    dictbike_profiles = Track.objects.values('profile').distinct().filter(user=request.user)

    listbike_profiles = ['All']
    for p in dictbike_profiles:
        try:
            listbike_profiles.append(p.get('profile').lower())
        except:
            pass

    listbike_profile_filters = []
    for lp in listbike_profiles:
        if lp:
            listbike_profile_filters.append(lp)
            alist= lp.split('+')
            for l in alist:
                listbike_profile_filters.append(l)
    
    profile_filters = list(set(listbike_profile_filters))
    profile_filters.sort()
 
    return profile_filters


@login_required(login_url='/login/')
def show_statistics(request):
    statistics_type = None
    if request.method == 'POST':
        statistics_type = request.POST.get('annual_statistics')

    if statistics_type:
        statistics_type = "annual"
    else:
        statistics_type = "profile"

    annual_statistics = "Statistics per year"
    profile_statistics = "Statistics per profile"

    bike_profile_filters = get_bike_profile_filters(request)

    first_year = int(get_first_date(request)[0:4])

    alltracks = []
    if statistics_type == "annual":
        page_headline = annual_statistics
        current_year = datetime.now().year
        while current_year >= first_year:
            date_start = str(current_year) + "-01-01"
            date_end = str(current_year) + "-12-31"
            stats_collection = []
            for profile_filter in bike_profile_filters:  
                tracks = get_tracks(request, date_start, date_end, None, profile_filter)
                statistics = compute_statistics(tracks)
                stats_collection.append({
                    "profile": profile_filter,
                    "statistics": statistics,
                })
            alltracks.append({
                "year": current_year,
                "stats_collection": stats_collection,
            })
            current_year -= 1
    else:
        page_headline = profile_statistics
        for profile_filter in bike_profile_filters:  
            stats_collection = []
            current_year = datetime.now().year
            while current_year >= first_year:
                date_start = str(current_year) + "-01-01"
                date_end = str(current_year) + "-12-31"
                tracks = get_tracks(request, date_start, date_end, None, profile_filter)
                statistics = compute_statistics(tracks)
                stats_collection.append({
                    "year": current_year,
                    "statistics": statistics,
                })
                current_year -= 1
            alltracks.append({
                    "profile": profile_filter,
                    "stats_collection": stats_collection,
                })
    

    return render(request, 'acstracks_app/show_statistics.html', {
        "page_headline": page_headline,
        "annual_statistics": annual_statistics,
        "profile_statistics": profile_statistics,
        "tracks": alltracks,
        }
    )


@login_required(login_url='/login/')
def heatmap(request, year, profile):
    if year == '0':
        date_start = get_first_date(request)
        date_end = datetime.now().strftime("%Y-%m-%d")
        year = "All"
    else:
        date_start = str(year) + "-01-01"
        date_end = str(year) + "-12-31"
    tracks = get_tracks(request, date_start, date_end, None, profile)
    statistics = compute_statistics(tracks)

    map_filename = (
        request.user.username+".html"
    )
    
    full_map_filename = (
        "/static/maps/" +
        request.user.username+".html"
    )

    all_tracks = []
    for atrack in tracks:
        all_tracks.append(gather_heatmap_data(request, atrack.storagefilename, map_filename))

    make_heatmap(request, all_tracks, map_filename)

    return render(request, 'acstracks_app/show_heartmap.html', {
        "year": year,
        "profile": profile,
        "statistics": statistics,
        'map_filename': full_map_filename,
        }
    )


def compute_statistics(tracks):
    statistics = {}

    total_length = float(0)
    total_avgspeed = float(0)
    highest_avgspeed = 0
    highest_maxspeed = 0
    longest_length = float(0)
    t0 = 0
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
        t0 = t0 + (
            (int(t.timelength.strftime("%H")) * 3600) +
            (int(t.timelength.strftime("%M")) * 60) +
            (int(t.timelength.strftime("%S")))
            )
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

    total_duration = (
        str(int(t0 / 3600)) + ":" +
        str(int(t0 % 3600 / 60)) + ":" +
        str(int(t0 % 3600 % 60))
    )
            
    statistics = {
        'number_of_tracks': tracks.count(),
        'total_length': total_length,
        'total_duration': total_duration,
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
    pattern = (r"^[A-z0-9\- +\ ]+$")
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
            maxspeedcappingfactor = data['maxspeedcappingfactor']
            show_avgspeed = data['show_avgspeed']
            show_maxspeed = data['show_maxspeed']
            show_totalascent = data['show_totalascent']
            show_totaldescent = data['show_totaldescent']
            show_avgcadence = data['show_avgcadence']
            show_avgheartrate = data['show_avgheartrate']
            gpx_contains_heartrate = data['gpx_contains_heartrate']
            gpx_contains_cadence = data['gpx_contains_cadence']

            try:
                preference = Preference.objects.get(user=request.user)
                old_speedthreshold = preference.speedthreshold
                old_elevationthreshold = preference.elevationthreshold
                old_maxspeedcappingfactor = preference.maxspeedcappingfactor
                preference.speedthreshold = speedthreshold
                preference.elevationthreshold = elevationthreshold
                preference.maxspeedcappingfactor = maxspeedcappingfactor
                preference.show_avgspeed = show_avgspeed
                preference.show_maxspeed = show_maxspeed
                preference.show_totalascent = show_totalascent
                preference.show_totaldescent = show_totaldescent
                preference.show_avgcadence = show_avgcadence
                preference.show_avgheartrate = show_avgheartrate
                preference.gpx_contains_heartrate = gpx_contains_heartrate
                preference.gpx_contains_cadence = gpx_contains_cadence
                preference.save()
            except:
                old_speedthreshold = settings.SPEEDTHRESHOLD
                old_elevationthreshold = settings.ELEVATIONTHRESHOLD
                old_maxspeedcappingfactor = settings.MAXSPEEDCAPPINGFACTOR
                preference = Preference.objects.create(
                    user=request.user,
                    speedthreshold=speedthreshold,
                    elevationthreshold=elevationthreshold,
                    maxspeedcappingfactor=maxspeedcappingfactor,
                    show_avgspeed=show_avgspeed,
                    show_maxspeed=show_maxspeed,
                    show_totalascent=show_totalascent,
                    show_totaldescent=show_totaldescent,
                    show_avgcadence=show_avgcadence,
                    show_avgheartrate=show_avgheartrate,
                    gpx_contains_heartrate=gpx_contains_heartrate,
                    gpx_contains_cadence=gpx_contains_cadence,
                )

            if (
                old_speedthreshold != speedthreshold or 
                old_elevationthreshold != elevationthreshold or
                old_maxspeedcappingfactor != maxspeedcappingfactor
            ):
                recalculate_tracks(request)
            return redirect('track_list')
    else:
        try:
            preference = Preference.objects.get(user=request.user)
            form = PreferenceForm(initial={
                'speedthreshold': preference.speedthreshold,
                'elevationthreshold': preference.elevationthreshold,
                'maxspeedcappingfactor': preference.maxspeedcappingfactor,
                'show_avgspeed': preference.show_avgspeed,
                'show_maxspeed': preference.show_maxspeed,
                'show_totalascent': preference.show_totalascent,
                'show_totaldescent': preference.show_totaldescent,
                'show_avgcadence': preference.show_avgcadence,
                'show_avgheartrate': preference.show_avgheartrate,
                'gpx_contains_heartrate': preference.gpx_contains_heartrate,
                'gpx_contains_cadence': preference.gpx_contains_cadence,
            })
        except:
            form = PreferenceForm()

    return render(request, 'acstracks_app/preference_form.html', {'form': form})


def recalculate_tracks(request):
    tracks = Track.objects.filter(user=request.user)
    for track in tracks:
        process_gpx_file(request, track.storagefilename, 0, track, False, False, False)

    return


@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def cleanup(request):
    fs = FileSystemStorage()

    if request.method == "POST":
        confirm_delete = request.POST.get('confirm_delete')
        if confirm_delete:
            try:
                obsolete_files = ast.literal_eval(request.POST.get('obsolete_files'))
                for fname, fsize in obsolete_files:
                    fs.delete(fname)
            except:
                return redirect('track_list')
    
    try:
        files = fs.listdir(settings.MEDIA_ROOT)[1]
        obsolete_files = []
        for f in files:
            if len(Track.objects.filter(storagefilename=f)) == 0:
                obsolete_files.append(tuple([f, int(((fs.size(f)/1024)+0.5))]))
    except:
        return redirect('track_list')

    return render(request, 'acstracks_app/cleanup.html', {
        'obsolete_files': obsolete_files, 
        }
    )
