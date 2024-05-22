from django.core.management.base import BaseCommand
from django.conf import settings
from dateutil.parser import parse
from decimal import Decimal
from pytz import timezone
from datetime import datetime
import time
import os
import gpxpy
import gpxpy.gpx
from acstracks_app.models import Track, User, Preference
from acstracks_app.exceptions import *
from acstracks_app.mapviews import *

class Command(BaseCommand):
    help = 'Recalculate trackeffort for all tracks'

    def handle(self, *args, **kwargs):
        # verbosity:
        #  0: only execute and save 
        #  1: display + execute and save 
        #  2: only display 
        
        # print("kwargs:" + str(kwargs))
        if "verbosity" in kwargs:
            verbosity = kwargs["verbosity"]
        if verbosity > 0:
            print(
                "username" + ";" +
                "displayfilename" + ";" +
                "created_date" + ";" +
                "name" + ";" +
                "profile" + ";" +
                "timelength" + ";" +
                "avgheartrate" + ";" +
                "trackeffort" + ";"
                "new trackeffort" + ";"
            )
        tracks = Track.objects.all()
        for track in tracks:
            if track.avgheartrate:
                new_trackeffort = self.process_gpxfile(track.storagefilename, track.avgheartrate, track.user)
                if verbosity > 0:
                    print(
                        track.user.username + ";" +
                        track.displayfilename + ";" +
                        track.created_date.strftime("%c") + ";" +
                        track.name + ";" +
                        track.profile + ";" +
                        track.timelength.strftime("%X") + ";" +
                        str(track.avgheartrate) + ";" +
                        str(track.trackeffort) + ";" +
                        str(new_trackeffort) + ";"
                    )
                if verbosity < 2:
                    track.trackeffort = new_trackeffort
                    track.save()

    def process_gpxfile(self, filename, avgheartrate, user):
        zone1 = 0
        zone2 = 0
        zone3 = 0
        zone4 = 0
        zone5 = 0
        newtrackeffort = 0

        try:
            preference = Preference.objects.get(user=user)
            maximum_heart_rate = preference.maximum_heart_rate
            resting_heart_rate = preference.resting_heart_rate
        except Exception:
            maximum_heart_rate = settings.MAXIMUM_HEART_RATE
            resting_heart_rate = preference.RESTING_HEART_RATE

        heart_rate_reserve = maximum_heart_rate - resting_heart_rate
        maximum_zone1 = resting_heart_rate + Decimal(round((settings.FACTOR_MAXIMUM_ZONE1 * float(heart_rate_reserve)), 0))
        maximum_zone2 = resting_heart_rate + Decimal(round((settings.FACTOR_MAXIMUM_ZONE2 * float(heart_rate_reserve)), 0))
        maximum_zone3 = resting_heart_rate + Decimal(round((settings.FACTOR_MAXIMUM_ZONE3 * float(heart_rate_reserve)), 0))
        maximum_zone4 = resting_heart_rate + Decimal(round((settings.FACTOR_MAXIMUM_ZONE4 * float(heart_rate_reserve)), 0))

        fullfilename = os.path.join(
            settings.MEDIA_ROOT,
            "gpx",
            filename
        )

        gpx_file = open(fullfilename, 'r')

        gpx = gpxpy.parse(gpx_file)

        previous_distance = 0
        previous_speed = -1
        cadence = 0
        timezone_info = timezone(settings.TIME_ZONE)
        previous_point = None
        distance = None

        for track in gpx.tracks:
            for segment in track.segments:
                for x, point in enumerate(segment.points):
                    if not point.time:
                        raise AcsFileNoActivity

                    distance = None
                    speed = None
                    heartrate = 0
                    for extension in point.extensions:
                        if extension.tag in settings.HEARTRATETAGS:
                            heartrate = int(extension.text)
                        if extension.tag in settings.CADENCETAGS:
                            cadence = int(extension.text)
                        for TrackPointExtension in extension:
                            if TrackPointExtension.tag in settings.HEARTRATETAGS:
                                heartrate = int(TrackPointExtension.text)
                            if TrackPointExtension.tag in settings.CADENCETAGS:
                                cadence = int(TrackPointExtension.text)

                    point_distance = calculate_using_haversine(
                        point, previous_point
                        )
                    if not distance:
                        distance = previous_distance + point_distance
                        previous_distance = distance
                        speed = None

                    point.time.astimezone(timezone_info).strftime(
                        "%Y-%m-%d %H:%M:%S"
                        )
                    if x > 0:
                        if distance < previous_distance:
                            distance = previous_distance
                            speed = previous_speed
                        tx = datetime.strptime(point.time.astimezone(
                            timezone_info).strftime(
                            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
                            )
                        txminus1 = datetime.strptime(previous_point.time.astimezone(
                            timezone_info).strftime(
                            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
                            )
                        duration = tx - txminus1

                        if not speed:
                            try:
                                speed = (
                                    point_distance / (
                                        duration.seconds
                                        )
                                    ) * 3.6
                            except Exception:
                                speed = 0

                        is_moving = (speed > settings.SPEEDTHRESHOLD) and (
                            not cadence or cadence > 0
                        )
                        if heartrate:
                            if is_moving:
                                if heartrate <= maximum_zone1:
                                    zone1 = zone1 + duration.seconds
                                elif heartrate <= maximum_zone2:
                                    zone2 = zone2 + duration.seconds
                                elif heartrate <= maximum_zone3:
                                    zone3 = zone3 + duration.seconds
                                elif heartrate <= maximum_zone4:
                                    zone4 = zone4 + duration.seconds
                                else:
                                    zone5 = zone5 + duration.seconds

                    else:
                        distance = 0
                        speed = 0
                        duration = 0
    
                    previous_point = point
                    previous_distance = distance
                    previous_speed = speed

        newtrackeffort = int(round(
            (math.sqrt((zone1 * settings.WEIGHT_ZONE1) + 
                       (zone2 * settings.WEIGHT_ZONE2) + 
                       (zone3 * settings.WEIGHT_ZONE3) + 
                       (zone4 * settings.WEIGHT_ZONE4) + 
                       (zone5 * settings.WEIGHT_ZONE5)))
              * (avgheartrate * avgheartrate) / settings.TRACKEFFORTFACTOR, 0))

        return newtrackeffort
    