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
            'link_to_detail_page',
            'show_is_public_track',
            'show_intermediate_points',
            'show_download_gpx',
            'show_heartrate',
            'show_cadence',
            'show_trackeffort',
            )
