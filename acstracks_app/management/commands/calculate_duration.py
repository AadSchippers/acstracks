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
    help = 'Calculate duration for all tracks'

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
                "movingduration" + ";" +
                "duration"
            )
        tracks = Track.objects.all()
        for track in tracks:
            if (track.maxheartrate or track.maxcadence):
                new_duration = self.process_gpxfile(track.storagefilename)
                if verbosity > 0:
                    print(
                        track.user.username + ";" +
                        track.displayfilename + ";" +
                        track.created_date.strftime("%c") + ";" +
                        track.name + ";" +
                        track.profile + ";" +
                        track.movingduration.strftime("%X") + ";" +
                        new_duration
                    )
                if verbosity < 2:
                    track.duration = new_duration
                    track.save()

    def process_gpxfile(self, filename):
        new_duration = None

        fullfilename = os.path.join(
            settings.MEDIA_ROOT,
            "gpx",
            filename
        )

        gpx_file = open(fullfilename, 'r')

        gpx = gpxpy.parse(gpx_file)

        timezone_info = timezone(settings.TIME_ZONE)

        for track in gpx.tracks:
            for segment in track.segments:
                if not segment.points[0].time:
                    raise AcsFileNoActivity
                last = len(segment.points) - 1
                strStartTime = str(segment.points[0])
                StartTime = strStartTime.split(" ")[1].split(":")
                StartTimeSeconds = (int(StartTime[0]) * 3600) + (int(StartTime[1]) * 60) + int(StartTime[2].split("+")[0])
                strEndTime = str(segment.points[last])
                EndTime = strEndTime.split(" ")[1].split(":")
                EndTimeSeconds = (int(EndTime[0]) * 3600) + (int(EndTime[1]) * 60) + int(EndTime[2].split("+")[0])
                new_duration = time.strftime(
                    '%H:%M:%S', time.gmtime(EndTimeSeconds - StartTimeSeconds)
                    )


        return new_duration
    
