from django import forms
from .models import Preference


class PreferenceForm(forms.ModelForm):

    class Meta:
        model = Preference
        fields = (
            'speedthreshold',
            'elevationthreshold',
            'maxspeedcappingfactor',
            'backgroundimage',
            'colorscheme',
            'force_recalculate',
            'show_backgroundimage',
            'show_avgspeed',
            'show_maxspeed',
            'show_totalascent',
            'show_totaldescent',
            'show_avgcadence',
            'show_avgheartrate',
            'show_is_public_track',
            'show_trackeffort',
            'privacy_zone',
            'default_profile',
            'maximum_heart_rate',
            'resting_heart_rate',
            )
