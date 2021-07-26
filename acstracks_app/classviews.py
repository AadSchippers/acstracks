from django.contrib.auth.views import LoginView, PasswordChangeView


class MyLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super(MyLoginView, self).get_context_data(**kwargs)

        context['page_name'] = "User"

        return context


class MyPasswordChangeView(PasswordChangeView):
    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        context['page_name'] = "User"

        return context
