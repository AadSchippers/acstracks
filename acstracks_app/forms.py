from django import forms
from .models import Preference


class PreferenceForm(forms.ModelForm):

    class Meta:
        model = Preference
        fields = (
            'speedthreshold',
            'elevationthreshold',
            'show_avgspeed',
            'show_maxspeed',
            'show_totalascent',
            'show_totaldescent',
            'show_avgcadence',
            'show_avgheartrate',
            )
