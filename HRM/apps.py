from django.apps import AppConfig


class HrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "HRM"


    def ready(self):
        import accounts.signals  # ← This MUST be here    
