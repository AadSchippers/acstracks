from django.core.management.base import BaseCommand
from django.conf import settings
from dateutil.parser import parse
from decimal import *
from pytz import timezone
from datetime import datetime
import time
import os
import gpxpy
import gpxpy.gpx
from acstracks_app.models import Track, User
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
                new_trackeffort = self.process_gpxfile(track.storagefilename, track.avgheartrate)
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

    def process_gpxfile(self, filename, avgheartrate):
        tsec140 = 0
        tsec150 = 0
        tsec160 = 0
        tsec180 = 0
        newtrackeffort = 0

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
                                if heartrate <= 140:
                                    tsec140 = tsec140 + duration.seconds
                                elif heartrate <= 160: 
                                    tsec150 = tsec150 + duration.seconds
                                elif heartrate <= 180: 
                                    tsec160 = tsec160 + duration.seconds
                                else:
                                    tsec180 = tsec180 + duration.seconds

                    else:
                        distance = 0
                        speed = 0
                        duration = 0
    
                    previous_point = point
                    previous_distance = distance
                    previous_speed = speed

        newtrackeffort = int(round(
            (math.sqrt((tsec140 * 0.75) + (tsec150 * 1) + (tsec160 * 1.5) + (tsec180 * 2)))
              * (avgheartrate * avgheartrate) / settings.TRACKEFFORTFACTOR, 0))

        return newtrackeffort
