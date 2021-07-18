from django import forms
from .models import Preference


class PreferenceForm(forms.ModelForm):

    class Meta:
        model = Preference
        fields = (
            'speedthreshold',
            'elevationthreshold',
            'maxspeedcappingfactor',
            'force_recalculate',
            'show_avgspeed',
            'show_maxspeed',
            'show_totalascent',
            'show_totaldescent',
            'show_avgcadence',
            'show_avgheartrate',
            'show_intermediate_points',
            'show_download_gpx',
            'gpx_contains_heartrate',
            'gpx_contains_cadence',
            )
