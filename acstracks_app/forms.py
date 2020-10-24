from django import forms
from .models import Threshold


class ThresholdForm(forms.ModelForm):

    class Meta:
        model = Threshold
        fields = ('speedthreshold', 'elevationthreshold',)
