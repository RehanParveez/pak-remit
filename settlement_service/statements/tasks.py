from celery import shared_task
from statements.models import BankStatement, SettlementMatch, SettlementDifference
from statements.services import SettlementService
from datetime import date

@shared_task
def process_uploaded_statement(statement_id):
  statement = BankStatement.objects.get(id=statement_id)
  statement.status = 'processing'
  statement.save()
  result = SettlementService.settlement_statement(statement_id)
  statement.status = 'completed'
  statement.save()
  return result

@shared_task
def settlement_report():
  today = date.today()
  matched = SettlementMatch.objects.filter(created_at__date=today, status = 'matched').count()
  unmatched = SettlementMatch.objects.filter(created_at__date=today, status = 'unmatched').count()
  differences = SettlementDifference.objects.filter(created_at__date=today, is_resolved=False).count()
  return {'matched': matched, 'unmatched': unmatched, 'differences': differences}