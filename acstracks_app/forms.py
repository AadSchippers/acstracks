from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Threshold

class ThresholdForm(forms.ModelForm):
    class Meta:
        model = Threshold
        fields = ('speedthreshold', 'elevationthreshold',)
