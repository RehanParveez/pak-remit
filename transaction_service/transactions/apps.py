from django.apps import AppConfig

class TransacionsConfig(AppConfig):
    name = 'transactions'
    
    def ready(self):
      import transactions.signals