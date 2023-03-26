from django.contrib.auth.views import LoginView, PasswordChangeView
from django.conf import settings
from .models import Preference
from .views import set_backgroundimage


class MyLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super(MyLoginView, self).get_context_data(**kwargs)

        context['page_name'] = "User"
        context['backgroundimage'] = "/static/img/acstracks" + settings.DEFAULT_COLORSCHEME + "bg.jpg"  
        context['colorscheme'] = settings.DEFAULT_COLORSCHEME
        context['primary_color'] = settings.PRIMARY_COLOR[settings.DEFAULT_COLORSCHEME]

        return context


class MyPasswordChangeView(PasswordChangeView):
    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        try:
            preference = Preference.objects.get(user=self.request.user)
            context['backgroundimage'] = set_backgroundimage(preference)
            context['colorscheme'] = preference.colorscheme
            context['primary_color'] = settings.PRIMARY_COLOR[preference.colorscheme]
        except Exception:
            context['backgroundimage'] = "/static/img/acstracks" + settings.DEFAULT_COLORSCHEME + "bg.jpg"  
            context['colorscheme'] = settings.DEFAULT_COLORSCHEME
            context['primary_color'] = settings.PRIMARY_COLOR[settings.DEFAULT_COLORSCHEME]

        context['page_name'] = "User"

        return context
