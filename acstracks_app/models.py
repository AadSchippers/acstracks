from django.conf import settings
from django.db import models
from django.utils import timezone


class Track(models.Model):
    filename = models.CharField(max_length=255, unique=True)
    creator = models.CharField(max_length=255)
    created_date = models.DateTimeField()
    name = models.CharField(max_length=255)
    profile = models.CharField(max_length=255)
    length = models.DecimalField(max_digits=6, decimal_places=2)
    timelength = models.TimeField()    
    avgspeed = models.DecimalField(max_digits=6, decimal_places=2)
    maxspeed = models.DecimalField(max_digits=6, decimal_places=2)
    totalascent = models.DecimalField(max_digits=6, decimal_places=2)
    totaldescent = models.DecimalField(max_digits=6, decimal_places=2)
    avgcadence = models.IntegerField(null=True, blank=True, default=None)
    maxcadence = models.IntegerField(null=True, blank=True, default=None)
    avgheartrate = models.IntegerField(null=True, blank=True, default=None)
    minheartrate = models.IntegerField(null=True, blank=True, default=None)
    maxheartrate = models.IntegerField(null=True, blank=True, default=None)

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (
            self.filename,
            self.created_date,
            self.name,
            self.creator,
            self.length,
            )

