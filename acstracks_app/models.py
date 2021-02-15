from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Track(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    displayfilename = models.CharField(max_length=255)
    storagefilename = models.CharField(max_length=255)
    creator = models.CharField(max_length=255)
    created_date = models.DateTimeField(default="00:00:00")
    name = models.CharField(max_length=255)
    profile = models.CharField(max_length=255, default="Fiets")
    length = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    timelength = models.TimeField(default="00:00:00")    
    avgspeed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    maxspeed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    totalascent = models.IntegerField(default=0)
    totaldescent = models.IntegerField(default=0)
    avgcadence = models.IntegerField(null=True, blank=True, default=None)
    maxcadence = models.IntegerField(null=True, blank=True, default=None)
    avgheartrate = models.IntegerField(null=True, blank=True, default=None)
    minheartrate = models.IntegerField(null=True, blank=True, default=None)
    maxheartrate = models.IntegerField(null=True, blank=True, default=None)
    publickey = models.CharField(max_length=255, null=True, blank=True, default=None)

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
    speedthreshold = models.DecimalField(max_digits=6, decimal_places=2, default=3.60)
    elevationthreshold = models.DecimalField(max_digits=6, decimal_places=2, default=0.25)
    show_avgspeed = models.BooleanField(default=True)
    show_maxspeed = models.BooleanField(default=True)
    show_totalascent = models.BooleanField(default=True)
    show_totaldescent = models.BooleanField(default=True)
    show_avgcadence = models.BooleanField(default=True)
    show_avgheartrate = models.BooleanField(default=True)

    def __str__(self):
        return "%s, %s, %s" % (
            self.user.username,
            self.speedthreshold,
            self.elevationthreshold,
            )
