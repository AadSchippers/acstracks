from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timezone import make_aware
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import HttpResponseRedirect
from django import forms
import xml.etree.ElementTree as ET
from .models import Track, Preference
from .forms import PreferenceForm
from .exceptions import *
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
def track_list(request):
    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )
    if preference.date_start is None:
        preference.date_start = get_first_date(request.user)
        preference.save()

    if preference.date_end is None:
        preference.date_end = datetime.now().strftime("%Y-%m-%d")
        preference.save()

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
            except Exception:
                pass
            storagefilename = fs.save(storagefilename, file)
            parse_file(request, storagefilename, file.name)

        if files or request.POST.get('Reset_filters'):
            preference.date_start = get_first_date(request.user)
            preference.date_end = datetime.now().strftime("%Y-%m-%d")
            preference.order_selected = "created_date_descending"
            preference.profile_filter = "All"
            preference.save()
        else:
            if request.POST.get('Date_start'):
                preference.date_start = request.POST.get('Date_start')
            if request.POST.get('Date_end'):
                preference.date_end = request.POST.get('Date_end')
            if request.POST.get('Order'):
                preference.order_selected = request.POST.get('Order')
            if request.POST.get('Profile'):
                preference.profile_filter = request.POST.get('Profile')
            preference.save()

    bike_profile_filters = get_bike_profile_filters(request)

    tracks = get_tracks(
        request,
        preference.date_start,
        preference.date_end,
        preference.order_selected,
        preference.profile_filter
        )

    statistics = compute_statistics(tracks)

    return render(request, 'acstracks_app/track_list.html', {
        'tracks': tracks,
        'preference': preference,
        'bike_profile_filters': bike_profile_filters,
        'statistics': statistics,
        'page_name': "Home",
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


def get_first_date(user):
    tracks = Track.objects.filter(
        user=user,
        ).order_by('created_date')

    try:
        date_start = tracks[0].created_date.strftime("%Y-%m-%d")
    except Exception:
        date_start = datetime.now().strftime("%Y-%m-%d")

    return date_start


@login_required(login_url='/login/')
def track_detail(request, pk):
    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

    try:
        atrack = Track.objects.get(id=pk, user=request.user)
    except Exception:
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

    public_url = (
        request.scheme + "://" +
        request.get_host() +
        "/publictrack/" +
        atrack.publickey
        )

    if request.method == 'POST':
        if request.POST.get('Intermediate_points'):
            try:
                preference.intermediate_points_selected = (
                    int(request.POST.get('Intermediate_points'))
                    )
            except Exception:
                preference.intermediate_points_selected = 0

            preference.save()

        name = request.POST.get('name_input')
        if is_input_valid(name):
            atrack.name = name
            atrack.save()
            return render(request, 'acstracks_app/track_detail.html', {
                'atrack': atrack,
                'map_filename': full_map_filename,
                'preference': preference,
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                'page_name': "Track detail",
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
                'preference': preference,
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                'page_name': "Track detail",
                }
            )

        public_track_changed = request.POST.get('public_track_changed')
        if public_track_changed:
            public_track = request.POST.get('public_track')
            atrack.public_track = (public_track == "on")
            atrack.save()
            return render(request, 'acstracks_app/track_detail.html', {
                'atrack': atrack,
                'map_filename': full_map_filename,
                'preference': preference,
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                'page_name': "Track detail",
                }
            )

        csvsave = request.POST.get('csvsave')

        confirm_delete = request.POST.get('confirm_delete')
        if confirm_delete:
            deletetrack(atrack)
            return redirect('track_list')

    if csvsave:
        return (
            process_gpx_file(
                request,
                atrack.storagefilename,
                preference.intermediate_points_selected,
                atrack,
                None,
                True,
                False
                )
        )
    elif atrack.length == 0:
        process_gpx_file(
            request, atrack.storagefilename,
            preference.intermediate_points_selected,
            atrack,
            map_filename,
            False,
            False
            )
    else:
        process_gpx_file(
            request,
            atrack.storagefilename,
            preference.intermediate_points_selected,
            None,
            map_filename,
            False,
            False
            )

    return render(request, 'acstracks_app/track_detail.html', {
                'atrack': atrack,
                'map_filename': full_map_filename,
                'preference': preference,
                'bike_profiles': bike_profiles,
                'public_url': public_url,
                'page_name': "Track detail",
        }
    )


def deletetrack(atrack):
    deletefile(atrack.storagefilename)
    atrack.delete()

    return


def deletefile(storagefilename):
    fs = FileSystemStorage()
    try:
        fs.delete(storagefilename)
    except Exception:
        pass

    return


def parse_file(
    request,
    storagefilename=None,
    displayfilename=None,
    intermediate_points_selected=0
):
    try:
        path = os.path.join(
            settings.MEDIA_ROOT,
            storagefilename
        )
        gpxfile = ET.parse(path)
    except Exception:
        deletefile(storagefilename)
        # error processing file, file skipped
        messages.error(
            request,
            "Error processing " +
            displayfilename +
            ", file skipped.")
        return

    namespace = settings.NAMESPACE
    gpxroot = gpxfile.getroot()
    creator = gpxroot.attrib['creator']
    try:
        metadata = gpxroot.find('ns:metadata', namespace)
        created_date = metadata.find('ns:time', namespace).text
    except Exception:
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

        try:
            process_gpx_file(
                request,
                trk.storagefilename,
                intermediate_points_selected,
                trk,
                False,
                False,
                False
                )
        except AcsFileNoActivity:
            deletetrack(trk)
            # error processing file, file skipped
            messages.error(
                request,
                displayfilename +
                " is not an activity file, " +
                " file skipped.")

    except Exception:
        pass

    return


def get_bike_profiles(request):
    dictbike_profiles = Track.objects.values(
        'profile'
        ).distinct().filter(user=request.user)

    listbike_profiles = ['All']
    for p in dictbike_profiles:
        try:
            listbike_profiles.append(p.get('profile').lower())
        except Exception:
            pass

    return listbike_profiles


def get_bike_profile_filters(request, multiple_profiles=True):
    dictbike_profiles = Track.objects.values(
        'profile'
        ).distinct().filter(user=request.user)

    listbike_profiles = ['All']
    for p in dictbike_profiles:
        try:
            listbike_profiles.append(p.get('profile').lower())
        except Exception:
            pass

    listbike_profile_filters = []
    for lp in listbike_profiles:
        if lp:
            if multiple_profiles:
                listbike_profile_filters.append(lp)
            alist = lp.split('+')
            for l1 in alist:
                listbike_profile_filters.append(l1)

    profile_filters = list(set(listbike_profile_filters))
    profile_filters.sort()

    return profile_filters


@login_required(login_url='/login/')
def show_statistics(request):
    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

    if request.method == 'POST':
        if request.POST.get('annual_statistics'):
            preference.statistics_type = "annual"
        else:
            preference.statistics_type = "profile"
        preference.save()

    annual_statistics = "Statistics per year"
    profile_statistics = "Statistics per profile"

    bike_profile_filters = get_bike_profile_filters(request)

    first_year = int(get_first_date(request.user)[0:4])

    alltracks = []
    if preference.statistics_type == "annual":
        page_headline = annual_statistics
        current_year = datetime.now().year
        while current_year >= first_year:
            date_start = str(current_year) + "-01-01"
            date_end = str(current_year) + "-12-31"
            stats_collection = []
            for profile in bike_profile_filters:
                tracks = get_tracks(
                    request, date_start, date_end, None, profile
                    )
                statistics = compute_statistics(tracks)
                stats_collection.append({
                    "profile": profile,
                    "statistics": statistics,
                })
            alltracks.append({
                "year": current_year,
                "stats_collection": stats_collection,
            })
            current_year -= 1
    else:
        page_headline = profile_statistics
        for profile in bike_profile_filters:
            stats_collection = []
            current_year = datetime.now().year
            while current_year >= first_year:
                date_start = str(current_year) + "-01-01"
                date_end = str(current_year) + "-12-31"
                tracks = get_tracks(
                    request, date_start, date_end, None, profile
                    )
                statistics = compute_statistics(tracks)
                stats_collection.append({
                    "year": current_year,
                    "statistics": statistics,
                })
                current_year -= 1
            alltracks.append({
                    "profile": profile,
                    "stats_collection": stats_collection,
                })

    return render(request, 'acstracks_app/show_statistics.html', {
        "page_headline": page_headline,
        "annual_statistics": annual_statistics,
        "profile_statistics": profile_statistics,
        "tracks": alltracks,
        "preference": preference,
        'page_name': "Statistics",
        }
    )


@login_required(login_url='/login/')
def heatmap(request, profile=None, year=None):
    date_start = None
    date_end = None

    if request.method == 'POST':
        date_start = request.POST.get('Date_start')
        date_end = request.POST.get('Date_end')
        profile = request.POST.get('Profile')
        # year = None

    if year:
        if year == '0':
            if not date_start:
                date_start = get_first_date(request.user)
            if not date_end:
                date_end = datetime.now().strftime("%Y-%m-%d")
            year = "All"
        else:
            if not date_start:
                date_start = str(year) + "-01-01"
            if not date_end:
                date_end = str(year) + "-12-31"
    else:
        try:
            preference = Preference.objects.get(user=request.user)
        except Exception:
            preference = Preference.objects.create(
                user=request.user,
            )

        if not date_start:
            date_start = preference.date_start

        if not date_end:
            date_end = preference.date_end

        if not profile:
            profile = preference.profile_filter

    tracks = get_tracks(
        request, date_start, date_end, None, profile
        )
    statistics = compute_statistics(tracks)

    bike_profile_filters = get_bike_profile_filters(request)

    map_filename = (
        request.user.username+"_heatmap.html"
    )

    full_map_filename = (
        "/static/maps/" +
        request.user.username+"_heatmap.html"
    )

    all_tracks = []
    for atrack in tracks:
        all_tracks.append(gather_heatmap_data(
            request, atrack.storagefilename, atrack.name, map_filename
            ))

    make_heatmap(request, all_tracks, map_filename)

    return render(request, 'acstracks_app/show_heatmap.html', {
        "profile_filter": profile,
        "bike_profile_filters": bike_profile_filters,
        "date_start": date_start,
        "date_end": date_end,
        "statistics": statistics,
        'map_filename': full_map_filename,
        'page_name': "Heatmap",
        }
    )


def compute_statistics(tracks):
    statistics = {}

    total_length = float(0)
    total_avgspeed = float(0)
    highest_avgspeed = 0
    highest_best20 = 0
    highest_best30 = 0
    highest_best60 = 0
    highest_maxspeed = 0
    longest_length = float(0)
    t0 = 0
    longest_duration = '00:00:00'
    max_ascent = float(0)
    max_descent = float(0)
    datetime_highest_avgspeed = datetime.now()
    datetime_highest_best20 = datetime.now()
    datetime_highest_best30 = datetime.now()
    datetime_highest_best60 = datetime.now()
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
        if highest_best20 < t.best20:
            highest_best20 = t.best20
            datetime_highest_best20 = t.created_date
        if highest_best30 < t.best30:
            highest_best30 = t.best30
            datetime_highest_best30 = t.created_date
        if highest_best60 < t.best60:
            highest_best60 = t.best60
            datetime_highest_best60 = t.created_date
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
        'highest_best20': highest_best20,
        'highest_best30': highest_best30,
        'highest_best60': highest_best60,
        'highest_maxspeed': highest_maxspeed,
        'longest_length': longest_length,
        'longest_duration': longest_duration,
        'max_ascent': max_ascent,
        'max_descent': max_descent,
        'datetime_highest_avgspeed': datetime_highest_avgspeed,
        'datetime_highest_best20': datetime_highest_best20,
        'datetime_highest_best30': datetime_highest_best30,
        'datetime_highest_best60': datetime_highest_best60,
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
    except Exception:
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
            force_recalculate = data['force_recalculate']
            show_avgspeed = data['show_avgspeed']
            show_maxspeed = data['show_maxspeed']
            show_totalascent = data['show_totalascent']
            show_totaldescent = data['show_totaldescent']
            show_avgcadence = data['show_avgcadence']
            show_avgheartrate = data['show_avgheartrate']
            show_is_public_track = data['show_is_public_track']
            link_to_detail_page = data['link_to_detail_page']
            show_intermediate_points = data['show_intermediate_points']
            show_download_gpx = data['show_download_gpx']
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
                preference.force_recalculate = force_recalculate
                preference.show_avgspeed = show_avgspeed
                preference.show_maxspeed = show_maxspeed
                preference.show_totalascent = show_totalascent
                preference.show_totaldescent = show_totaldescent
                preference.show_avgcadence = show_avgcadence
                preference.show_avgheartrate = show_avgheartrate
                preference.show_is_public_track = show_is_public_track
                preference.link_to_detail_page = link_to_detail_page
                preference.show_intermediate_points = show_intermediate_points
                preference.show_download_gpx = show_download_gpx
                preference.gpx_contains_heartrate = gpx_contains_heartrate
                preference.gpx_contains_cadence = gpx_contains_cadence
                preference.save()
            except Exception:
                old_speedthreshold = settings.SPEEDTHRESHOLD
                old_elevationthreshold = settings.ELEVATIONTHRESHOLD
                old_maxspeedcappingfactor = settings.MAXSPEEDCAPPINGFACTOR
                preference = Preference.objects.create(
                    user=request.user,
                    speedthreshold=speedthreshold,
                    elevationthreshold=elevationthreshold,
                    maxspeedcappingfactor=maxspeedcappingfactor,
                    force_recalculate=force_recalculate,
                    show_avgspeed=show_avgspeed,
                    show_maxspeed=show_maxspeed,
                    show_totalascent=show_totalascent,
                    show_totaldescent=show_totaldescent,
                    show_avgcadence=show_avgcadence,
                    show_avgheartrate=show_avgheartrate,
                    show_is_public_track=show_is_public_track,
                    link_to_detail_page=link_to_detail_page,
                    show_intermediate_points=show_intermediate_points,
                    show_download_gpx=show_download_gpx,
                    gpx_contains_heartrate=gpx_contains_heartrate,
                    gpx_contains_cadence=gpx_contains_cadence,
                )

            if (
                force_recalculate or
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
                'maxspeedcappingfactor': preference.maxspeedcappingfactor,
                'force_recalculate': preference.force_recalculate,
                'show_avgspeed': preference.show_avgspeed,
                'show_maxspeed': preference.show_maxspeed,
                'show_totalascent': preference.show_totalascent,
                'show_totaldescent': preference.show_totaldescent,
                'show_avgcadence': preference.show_avgcadence,
                'show_avgheartrate': preference.show_avgheartrate,
                'show_is_public_track': preference.show_is_public_track,
                'link_to_detail_page': preference.link_to_detail_page,
                'show_intermediate_points':
                    preference.show_intermediate_points,
                'show_download_gpx': preference.show_download_gpx,
                'gpx_contains_heartrate': preference.gpx_contains_heartrate,
                'gpx_contains_cadence': preference.gpx_contains_cadence,
            })
        except Exception:
            form = PreferenceForm()

    return render(
        request, 'acstracks_app/preference_form.html', {
            'form': form,
            'page_name': "Preferences",
            }
        )


def recalculate_tracks(request):
    tracks = Track.objects.filter(user=request.user)
    for track in tracks:
        process_gpx_file(
            request, track.storagefilename, 0, track, False, False, False
            )

    return


@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def cleanup(request):
    fs = FileSystemStorage()

    if request.method == "POST":
        confirm_delete = request.POST.get('confirm_delete')
        if confirm_delete:
            try:
                obsolete_files = ast.literal_eval(
                    request.POST.get('obsolete_files')
                    )
                for fname, fsize in obsolete_files:
                    fs.delete(fname)
            except Exception:
                return redirect('track_list')

    try:
        files = fs.listdir(settings.MEDIA_ROOT)[1]
        obsolete_files = []
        for f in files:
            if len(Track.objects.filter(storagefilename=f)) == 0:
                obsolete_files.append(tuple([f, int(((fs.size(f)/1024)+0.5))]))
    except Exception:
        return redirect('track_list')

    return render(request, 'acstracks_app/cleanup.html', {
        'obsolete_files': obsolete_files,
        'page_name': "Preferences",
        }
    )


@login_required(login_url='/login/')
def publish(request):
    if request.method == "POST":
        profile = request.POST.get('Profile')

        if profile:
            map_filename = (
                request.user.username+"_"+profile+"_public.html"
            )
            if profile == "All":
                tracks = Track.objects.filter(
                    user=request.user,
                    public_track=True,
                    )
            else:
                tracks = Track.objects.filter(
                    user=request.user,
                    public_track=True,
                    profile__icontains=profile,
                    )

            all_tracks = []
            for atrack in tracks:
                all_tracks.append(gather_heatmap_data(
                    request, atrack.storagefilename, atrack.name, map_filename
                    ))

            make_heatmap(
                request, all_tracks, map_filename,
                settings.LINE_COLOR, settings.NORMAL_OPACITY, True
                )

    tracks = Track.objects.filter(
        user=request.user,
        public_track=True,
        )

    try:
        statistics = compute_statistics(tracks)
    except Exception:
        statistics = {}

    bike_profile_filters = get_bike_profile_filters(request, False)

    fs = FileSystemStorage(location='')
    files = fs.listdir(settings.MAPS_ROOT)[1]
    published_files = []
    for f in files:
        if f.startswith(request.user.username+"_"):
            if f.endswith("_public.html"):
                published_name = f.split(
                    request.user.username+'_')[1].rsplit('_public.html'
                    )[0]
                published_url = (
                    request.scheme + "://" +
                    request.get_host() +
                    "/public/" +
                    request.user.username +
                    "/" +
                    published_name
                    )
                published_href = published_url.replace(' ', '%20')

                published_files.append(tuple(
                    [published_name, published_url, published_href]
                    ))

    return render(request, 'acstracks_app/publish.html', {
        'tracks': tracks,
        'statistics': statistics,
        'bike_profile_filters': bike_profile_filters,
        'published_files': published_files,
        'page_name': "Publish",
        }
    )


def public_tracks(request, username=None, profile=None):
    tracks = []
    statistics = {}
    link_to_detail_page = False

    public_url = (
        request.scheme + "://" +
        request.get_host() +
        "/publictrack/"
        )

    basemap_filename = (
        "/static/maps/" +
        "public_base.html"
    )

    full_map_filename = basemap_filename

    if username and profile:
        try:
            user = User.objects.get(username=username)
            if profile == "All":
                tracks = Track.objects.filter(
                    user=user,
                    public_track=True,
                    )
            else:
                tracks = Track.objects.filter(
                    user=user,
                    public_track=True,
                    profile__icontains=profile,
                    )
        except Exception:
            tracks = []

        try:
            preference = Preference.objects.get(user=user)
            link_to_detail_page = preference.link_to_detail_page
        except Exception:
            link_to_detail_page = False

        try:
            statistics = compute_statistics(tracks)
        except Exception:
            statistics = {}

        full_map_filename = (
            "/static/maps/" +
            username+"_"+profile.replace(' ', '%20')+"_public.html"
        )

    return render(request, 'acstracks_app/publictracks.html', {
        'tracks': tracks,
        'statistics': statistics,
        'public_url': public_url,
        'link_to_detail_page': link_to_detail_page,
        'map_filename': full_map_filename,
        'basemap_filename': basemap_filename,
        }
    )


def publictrack_detail(request, publickey, intermediate_points_selected=None):
    if not intermediate_points_selected:
        intermediate_points_selected = 0

    try:
        atrack = Track.objects.get(publickey=publickey)
    except Exception:
        return redirect('track_list')

    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

    map_filename = (
        atrack.user.username+"-public.html"
    )

    full_map_filename = (
        "/static/maps/" +
        atrack.user.username+"-public.html"
    )

    gpxdownload = None

    if request.method == 'POST':
        intermediate_points_selected = request.POST.get('Intermediate_points')
        gpxdownload = request.POST.get('gpxdownload')

    if gpxdownload == 'True':
        return process_gpx_file(
            request,
            atrack.storagefilename,
            intermediate_points_selected,
            atrack,
            None,
            False,
            True
        )

    process_gpx_file(
        request,
        atrack.storagefilename,
        intermediate_points_selected,
        None,
        map_filename,
        False,
        False
        )

    return render(request, 'acstracks_app/publictrack_detail.html', {
        'atrack': atrack,
        'preference': preference,
        'map_filename': full_map_filename,
        'intermediate_points_selected': int(intermediate_points_selected),
        'page_name': "Publish",
        }
    )
