from django.apps import AppConfig

class RatesConfig(AppConfig):
    name = 'rates'
    
    def ready(self):
      import rates.signals
