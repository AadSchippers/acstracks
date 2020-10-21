from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Track(models.Model):
    username = models.CharField(max_length=150)
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
    totalascent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    totaldescent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avgcadence = models.IntegerField(null=True, blank=True, default=None)
    maxcadence = models.IntegerField(null=True, blank=True, default=None)
    avgheartrate = models.IntegerField(null=True, blank=True, default=None)
    minheartrate = models.IntegerField(null=True, blank=True, default=None)
    maxheartrate = models.IntegerField(null=True, blank=True, default=None)

    class Meta:
        unique_together = ('username', 'displayfilename')

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (
            self.username,
            self.displayfilename,
            self.created_date,
            self.name,
            self.length,
            )

