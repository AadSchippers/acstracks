from django.contrib.auth.views import LoginView, PasswordChangeView
from django.conf import settings


class MyLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super(MyLoginView, self).get_context_data(**kwargs)

        context['page_name'] = "User"
        context['colorscheme'] = settings.DEFAULT_COLORSCHEME
        context['primary_color'] = settings.PRIMARY_COLOR[settings.DEFAULT_COLORSCHEME]

        return context


class MyPasswordChangeView(PasswordChangeView):
    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        context['page_name'] = "User"
        context['colorscheme'] = settings.DEFAULT_COLORSCHEME
        context['primary_color'] = settings.PRIMARY_COLOR[settings.DEFAULT_COLORSCHEME]

        return context
