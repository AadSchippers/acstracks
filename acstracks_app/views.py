from django.db import IntegrityError
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
            fs = FileSystemStorage(location=settings.MEDIA_ROOT + "/gpx")
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

        csvexport = request.POST.get('csvexport')
        if csvexport: 
            return exporttracks(request)

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
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
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

    if order_selected == "trackeffort_descending":
        order_by = "-trackeffort"

    if order_selected == "trackeffort_ascending":
        order_by = "trackeffort"

    date_start = make_aware(parse(date_start + " 00:00:00"))
    date_end = make_aware(parse(date_end + " 23:59:59"))

    try:
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
    except Exception as e:
        if len(e.args) > 0:
            messagetext = e.args[0] + " "
        else:
            messagetext = type(e)
        messages.error(
            request,
            "Error retrieving files: " +
            messagetext
            )
        return

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
        settings.MAPS_URL +
        atrack.user.username+".html"
    )

    if len(atrack.displayfilename) > 28:
        displayfilename = atrack.displayfilename[:25] + "..."
    else:
        displayfilename = atrack.displayfilename
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
                'colorscheme': preference.colorscheme,
                'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
                'backgroundimage': set_backgroundimage(preference),
                'atrack': atrack,
                'displayfilename': displayfilename,
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
                'colorscheme': preference.colorscheme,
                'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
                'backgroundimage': set_backgroundimage(preference),
                'atrack': atrack,
                'displayfilename': displayfilename,
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
                'colorscheme': preference.colorscheme,
                'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
                'backgroundimage': set_backgroundimage(preference),
                'atrack': atrack,
                'displayfilename': displayfilename,
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
            True,
            False,
            False
            )
    else:
        process_gpx_file(
            request,
            atrack.storagefilename,
            preference.intermediate_points_selected,
            atrack,
            map_filename,
            False,
            False,
            False
            )

    return render(request, 'acstracks_app/track_detail.html', {
                'colorscheme': preference.colorscheme,
                'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
                'backgroundimage': set_backgroundimage(preference),
                'atrack': atrack,
                'displayfilename': displayfilename,
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
    fs = FileSystemStorage(location=settings.MEDIA_ROOT + "/gpx")
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
            settings.MEDIA_ROOT + "/gpx",
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
    try:
        gpxtrk = gpxroot.find('ns:trk', namespace)
        name = gpxtrk.find('ns:name', namespace).text
        extensions = gpxtrk.find('ns:extensions', namespace)
    except Exception:
        # error processing file, file skipped
        messagetext = "Error processing "
        messages.error(
            request,
            messagetext +
            displayfilename +
            ", file skipped.")
        return

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
                None,
                True,
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
            return

    except IntegrityError:
        # error processing file, file skipped
        messages.error(
            request,
            "Error processing " +
            displayfilename +
            ", file skipped because already present.")
        return

    except Exception as e:
        # error processing file, file skipped
        if len(e.args) > 0:
            messagetext = e.args[0] + " "
        else:
            messagetext = "Error processing "
        messages.error(
            request,
            messagetext +
            displayfilename +
            ", file skipped.")
        return

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
    profile_statistics = "Statistics per tag"

    bike_profile_filters = get_bike_profile_filters(request)

    first_year = int(get_first_date(request.user)[0:4])
    last_year = datetime.now().year


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
            date_start = str(first_year) + "-01-01"
            date_end = str(last_year) + "-12-31"
            tracks = get_tracks(
                request, date_start, date_end, None, profile
                )
            statistics = compute_statistics(tracks)
            stats_collection.append({
                "year": "Total",
                "statistics": statistics,
            })
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
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
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

    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

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
        settings.MAPS_URL +
        request.user.username+"_heatmap.html"
    )

    all_tracks = []
    for atrack in tracks:
        all_tracks.append(gather_heatmap_data(
            request, atrack.storagefilename, atrack.name, map_filename
            ))

    make_heatmap(request, all_tracks, map_filename, preference.colorscheme)

    return render(request, 'acstracks_app/show_heatmap.html', {
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
        "profile_filter": profile,
        "bike_profile_filters": bike_profile_filters,
        "date_start": date_start,
        "date_end": date_end,
        "statistics": statistics,
        'map_filename': full_map_filename,
        'preference': preference,
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

    # total_length = round((total_length), 2)
    total_length = "{:.2f}".format(total_length)

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


def set_backgroundimage(preference):
    if preference == None:
        return "/static/img/acstracks" + settings.DEFAULT_COLORSCHEME + "bg.jpg"
    
    if not preference.show_backgroundimage:
        return None
    
    if preference.backgroundimage:
        return "/static/media/" + preference.backgroundimage.name
    
    return "/static/img/acstracks" + preference.colorscheme + "bg.jpg"


def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')
    # Redirect to a success page.


@login_required(login_url='/login/')
def process_preferences(request):
    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )
    form = PreferenceForm()
    if request.method == "POST":
        form = PreferenceForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            defaultappearence = (request.POST.get("defaultappearence") is not None)
            speedthreshold = data['speedthreshold']
            elevationthreshold = data['elevationthreshold']
            maxspeedcappingfactor = data['maxspeedcappingfactor']
            force_recalculate = data['force_recalculate']
            backgroundimage = data['backgroundimage']
            colorscheme = data['colorscheme']
            show_backgroundimage = data['show_backgroundimage']
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
            show_heartrate = data['show_heartrate']
            show_cadence = data['show_cadence']
            show_trackeffort = data['show_trackeffort']
            show_trackeffort_public = data['show_trackeffort_public']

            old_backgroundimage = preference.backgroundimage
            preference.speedthreshold = speedthreshold
            preference.elevationthreshold = elevationthreshold
            preference.maxspeedcappingfactor = maxspeedcappingfactor
            preference.force_recalculate = force_recalculate
            preference.show_backgroundimage = show_backgroundimage
            if backgroundimage:
                preference.show_backgroundimage = True
                preference.backgroundimage = backgroundimage
            preference.colorscheme = colorscheme
            if defaultappearence:
                preference.backgroundimage = None
                preference.colorscheme = settings.DEFAULT_COLORSCHEME
                preference.show_backgroundimage = True
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
            preference.show_heartrate = show_heartrate
            preference.show_cadence = show_cadence
            preference.show_trackeffort = show_trackeffort
            preference.show_trackeffort_public = show_trackeffort_public
            preference.save()
            if old_backgroundimage:
                if old_backgroundimage.name != preference.backgroundimage.name:
                    fs = FileSystemStorage(location=settings.MEDIA_ROOT + "/img")
                    try:
                        fs.delete(old_backgroundimage.name[4:])
                    except Exception:
                        pass
 

            if force_recalculate:
                recalculate_tracks(request)
            
            return redirect('preference')
        else:
            form = get_preferenceform(request)
    else:
        form = get_preferenceform(request)

    return render(
        request, 'acstracks_app/preference_form.html', {
            'form': form,
            'colorscheme': preference.colorscheme,
            'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
            'backgroundimage': set_backgroundimage(preference),
            'allcolorschemes': settings.COLORSCHEMES,            
            'page_name': "Preferences",
            }
        )


def get_preferenceform(request):
    try:
        preference = Preference.objects.get(user=request.user)
        form = PreferenceForm(initial={
            'speedthreshold': preference.speedthreshold,
            'elevationthreshold': preference.elevationthreshold,
            'maxspeedcappingfactor': preference.maxspeedcappingfactor,
            'force_recalculate': False,
            'backgroundimage': preference.backgroundimage,
            'colorscheme': preference.colorscheme,
            'show_backgroundimage': preference.show_backgroundimage,
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
            'show_heartrate': preference.show_heartrate,
            'show_cadence': preference.show_cadence,
            'show_trackeffort': preference.show_trackeffort,
            'show_trackeffort_public': preference.show_trackeffort_public,
        })
    except Exception:
        form = PreferenceForm()

    return form


def recalculate_tracks(request):
    tracks = Track.objects.filter(user=request.user)
    for track in tracks:
        process_gpx_file(
            request, track.storagefilename, 0, track, None, True, False, False
            )

    return


@user_passes_test(lambda u: u.is_superuser, login_url='/login/')
def cleanup(request):
    fs = FileSystemStorage(location=settings.MEDIA_ROOT)

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

    obsolete_files = []
    try:
        files = fs.listdir(settings.MEDIA_ROOT + "/gpx")[1]
        for f in files:
            if len(Track.objects.filter(storagefilename=f)) == 0:
                obsolete_files.append(tuple(["./gpx/" + f, int(((fs.size("./gpx/"+ f)/1024)+0.5))]))
    except Exception:
        pass
    try:
        files = fs.listdir(settings.MEDIA_ROOT + "/img")[1]
        for f in files:
            if len(Preference.objects.filter(backgroundimage="img/" + f)) == 0:
                obsolete_files.append(tuple(["./img/" + f, int(((fs.size("./img/"+ f)/1024)+0.5))]))
    except Exception:
        pass

    try:
        preference = Preference.objects.get(user=request.user)
        colorscheme = preference.colorscheme
    except:
        colorscheme = settings.DEFAULT_COLORSCHEME

    return render(request, 'acstracks_app/cleanup.html', {
        'colorscheme': colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
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

            try:
                preference = Preference.objects.get(user=request.user)
                colorscheme = preference.colorscheme
            except:
                colorscheme = settings.DEFAULT_COLORSCHEME

            make_heatmap(
                request, all_tracks,
                map_filename,
                colorscheme,
                settings.NORMAL_OPACITY,
                settings.MAP_LINE_WEIGHT,
                True
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

    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        preference = Preference.objects.create(
            user=request.user,
        )

    fs = FileSystemStorage(location=settings.MAPS_ROOT)
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

                if published_name != 'public.html':
                    published_files.append(tuple(
                        [published_name, published_url, published_href]
                    ))

    return render(request, 'acstracks_app/publish.html', {
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
        'tracks': tracks,
        'statistics': statistics,
        'bike_profile_filters': bike_profile_filters,
        'published_files': published_files,
        'preference': preference,
        'page_name': "Publish",
        }
    )


@login_required(login_url='/login/')
def unpublish(request, profile=None):
    fs = FileSystemStorage(location=settings.MAPS_ROOT)
    map_filename = (
        settings.MAPS_ROOT +
        "/" +
        request.user.username +
        "_" +
        profile+"_public.html"
    )
    if fs.exists(map_filename):
        try:
            fs.delete(map_filename)
        except Exception:
            pass

    return redirect('publish')


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
        settings.MAPS_URL +
        "public_base.html"
    )

    full_map_filename = basemap_filename

    if username and profile:
        fs = FileSystemStorage(location=settings.MAPS_ROOT)
        map_filename = username+"_"+profile+"_public.html"
        if fs.exists(settings.MAPS_ROOT+"/"+map_filename):
            try:
                user = User.objects.get(username=username)
                if profile == "All":
                    tracks = Track.objects.filter(
                        user=user,
                        public_track=True,
                        ).order_by('created_date')
                else:
                    tracks = Track.objects.filter(
                        user=user,
                        public_track=True,
                        profile__icontains=profile,
                        ).order_by('created_date')
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
                settings.MAPS_URL +
                map_filename.replace(' ', '%20')
            )

        else:
            full_map_filename = basemap_filename
            tracks = []
            link_to_detail_page = False
            statistics = {}

    return render(request, 'acstracks_app/publictracks.html', {
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
        'tracks': tracks,
        'username': username,
        'profile': profile,
        'statistics': statistics,
        'public_url': public_url,
        'link_to_detail_page': link_to_detail_page,
        'preference': preference,
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
        preference = Preference.objects.get(user=atrack.user)
        show_intermediate_points = preference.show_intermediate_points
        show_heartrate = preference.show_heartrate
        show_cadence = preference.show_cadence
        show_trackeffort_public = preference.show_trackeffort_public
        show_download_gpx = preference.show_download_gpx
    except Exception:
        show_intermediate_points = False
        show_heartrate = False
        show_cadence = False
        show_trackeffort_public = False
        show_download_gpx = False

    map_filename = (
        atrack.user.username+"_public.html"
    )

    full_map_filename = (
        settings.MAPS_URL +
        atrack.user.username+"_public.html"
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
            True,
            False,
            True
        )

    process_gpx_file(
        request,
        atrack.storagefilename,
        intermediate_points_selected,
        atrack,
        map_filename,
        False,
        False,
        False
        )

    return render(request, 'acstracks_app/publictrack_detail.html', {
        'colorscheme': preference.colorscheme,
        'primary_color': settings.PRIMARY_COLOR[preference.colorscheme],
        'backgroundimage': set_backgroundimage(preference),
        'atrack': atrack,
        'show_intermediate_points': show_intermediate_points,
        'show_heartrate': show_heartrate,
        'show_cadence': show_cadence,
        'show_download_gpx': show_download_gpx,
        'show_trackeffort_public': show_trackeffort_public,
        'preference': preference,
        'map_filename': full_map_filename,
        'intermediate_points_selected': int(intermediate_points_selected),
        'page_name': "Publish",
        }
    )

@login_required(login_url='/login/')
def exporttracks(request):
    try:
        preference = Preference.objects.get(user=request.user)
    except Exception:
        return

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    csvfilename = request.user.username+"_alltracks"+".csv"
    response['Content-Disposition'] = 'attachment; filename="'+csvfilename+'"'

    writer = csv.writer(response)

    writer.writerow([
        'displayfilename', 
        'creator', 
        'created_date', 
        'name', 
        'profile', 
        'length', 
        'timelength', 
        'avgspeed', 
        'best20', 
        'best30', 
        'best60', 
        'maxspeed', 
        'totalascent', 
        'totaldescent', 
        'avgcadence', 
        'maxcadence', 
        'avgheartrate', 
        'minheartrate', 
        'maxheartrate', 
        'trackeffort',
        'public_track',
        ])

    AllTracks = Track.objects.filter(user=request.user)
    for aTrack in AllTracks:
        writer.writerow([
            aTrack.displayfilename, 
            aTrack.creator, 
            aTrack.created_date, 
            aTrack.name, 
            aTrack.profile, 
            aTrack.length, 
            aTrack.timelength, 
            aTrack.avgspeed, 
            aTrack.best20, 
            aTrack.best30, 
            aTrack.best60, 
            aTrack.maxspeed, 
            aTrack.totalascent, 
            aTrack.totaldescent, 
            aTrack.avgcadence, 
            aTrack.maxcadence, 
            aTrack.avgheartrate, 
            aTrack.minheartrate, 
            aTrack.maxheartrate, 
            aTrack.trackeffort, 
            aTrack.public_track, 
            ])

    return response

