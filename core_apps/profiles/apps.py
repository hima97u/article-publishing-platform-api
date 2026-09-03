from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProfilesConfig(AppConfig):
    name = "core_apps.profiles"
    verbose_name = _("Profiles")
    
    def ready(self):
        from core_apps.profiles import signals

    
