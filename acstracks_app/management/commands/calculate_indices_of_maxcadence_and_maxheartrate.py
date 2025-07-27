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
    help = 'Recalculate indices of maxcadence and maxheartrate for all tracks'

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
                "maxcadence_pointindex" + ";" +
                "new maxcadence_pointindex" + ";"
                "maxheartrate_pointindex" + ";"
                "new maxheartrate_pointindex" + ";"
            )
        tracks = Track.objects.all()
        for track in tracks:
            if (track.maxheartrate or track.maxcadence):
                new_pointindices = self.process_gpxfile(track.storagefilename, track.maxcadence, track.maxheartrate)
                if verbosity > 0:
                    print(
                        track.user.username + ";" +
                        track.displayfilename + ";" +
                        track.created_date.strftime("%c") + ";" +
                        track.name + ";" +
                        track.profile + ";" +
                        track.movingduration.strftime("%X") + ";" +
                        str(track.maxcadence_pointindex) + ";" +
                        str(new_pointindices[0]) + ";" +
                        str(track.maxheartrate_pointindex) + ";" +
                        str(new_pointindices[1]) + ";"
                    )
                if verbosity < 2:
                    track.maxcadence_pointindex = new_pointindices[0]
                    track.maxheartrate_pointindex = new_pointindices[1]
                    track.save()

    def process_gpxfile(self, filename, maxcadence, maxheartrate):
        new_pointindices = []
        new_maxcadence_pointindex = 0
        new_maxheartrate_pointindex = 0

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

                    cadence = 0
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

                    if cadence == maxcadence:
                        new_maxcadence_pointindex = x
                    if heartrate == maxheartrate:
                        new_maxheartrate_pointindex = x

        new_pointindices.append(new_maxcadence_pointindex)
        new_pointindices.append(new_maxheartrate_pointindex) 

        return new_pointindices
