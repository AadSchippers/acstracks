from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime


class Track(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    displayfilename = models.CharField(max_length=255)
    storagefilename = models.CharField(max_length=255)
    creator = models.CharField(max_length=255)
    created_date = models.DateTimeField(default="00:00:00")
    name = models.CharField(max_length=255)
    profile = models.CharField(
        max_length=255, null=True, blank=True, default=None
        )
    length = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    timelength = models.TimeField(default="00:00:00")
    avgspeed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    best20 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    best20_start_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    best20_end_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    best30 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    best30_start_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    best30_end_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    best60 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    best60_start_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    best60_end_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    maxspeed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    maxspeed_pointindex = models.DecimalField(max_digits=6, decimal_places=0, default=0)
    totalascent = models.IntegerField(default=0)
    totaldescent = models.IntegerField(default=0)
    avgcadence = models.IntegerField(null=True, blank=True, default=None)
    maxcadence = models.IntegerField(null=True, blank=True, default=None)
    avgheartrate = models.IntegerField(null=True, blank=True, default=None)
    minheartrate = models.IntegerField(null=True, blank=True, default=None)
    maxheartrate = models.IntegerField(null=True, blank=True, default=None)
    trackeffort = models.IntegerField(null=True, blank=True, default=None)
    public_track = models.BooleanField(default=False)
    publickey = models.CharField(
        max_length=255, null=True, blank=True, default=None
        )

    class Meta:
        unique_together = ('user', 'displayfilename')

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (
            self.user.username,
            self.displayfilename,
            self.created_date,
            self.name,
            self.length,
            )


class Preference(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    speedthreshold = models.DecimalField(
        max_digits=6, decimal_places=2, default=3.60
        )
    elevationthreshold = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.25
        )
    maxspeedcappingfactor = models.DecimalField(
        max_digits=6, decimal_places=2, default=1.25
        )
    force_recalculate = models.BooleanField(default=False)
    backgroundimage = models.FileField(upload_to="img",
        max_length=255, null=True, blank=True, default=None
        )
    show_avgspeed = models.BooleanField(default=True)
    show_maxspeed = models.BooleanField(default=True)
    show_totalascent = models.BooleanField(default=True)
    show_totaldescent = models.BooleanField(default=True)
    show_avgcadence = models.BooleanField(default=True)
    show_avgheartrate = models.BooleanField(default=True)
    show_trackeffort = models.BooleanField(default=True)
    show_is_public_track = models.BooleanField(default=True)
    # Preferences for public page
    link_to_detail_page = models.BooleanField(default=False)
    show_intermediate_points = models.BooleanField(default=False)
    show_download_gpx = models.BooleanField(default=False)
    show_heartrate = models.BooleanField(default=False)
    show_cadence = models.BooleanField(default=False)
    show_trackeffort_public = models.BooleanField(default=False)
    date_start = models.CharField(
        max_length=255, null=True, blank=True, default=None
        )
    date_end = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=datetime.now().strftime("%Y-%m-%d")
        )
    profile_filter = models.CharField(
        max_length=255, null=True, blank=True, default="All"
        )
    order_selected = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default="created_date_descending"
        )
    intermediate_points_selected = models.DecimalField(
        max_digits=6, decimal_places=0, default=0
        )
    statistics_type = models.CharField(
        max_length=255, null=True, blank=True, default="annual"
        )

    def __str__(self):
        return "%s, %s, %s" % (
            self.user.username,
            self.speedthreshold,
            self.elevationthreshold,
            )
