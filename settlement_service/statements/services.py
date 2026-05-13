from statements.models import BankStatement, BankTransaction, SettlementMatch, SettlementDifference
import io
import csv
from decimal import Decimal

class StatementParserService:
  @staticmethod
  def parse_csv(file, statement):
    decoded_file = file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
        
    transactions = []
    for row in reader:
      transaction = BankTransaction.objects.create(statement=statement, transaction_date=row['date'], amount=Decimal(row['amount']),  description=row['description'],
        reference_number=row.get('reference', ''), transaction_type=row['type'].lower())
      transactions.append(transaction)
    return transactions

class MatchingEngine:
  @staticmethod
  def auto_match(statement_id):
    statement = BankStatement.objects.get(id=statement_id)
    bank_transactions = BankTransaction.objects.filter(statement=statement)
        
    matched_count = 0
    for bank_txn in bank_transactions:
      confidence = MatchingEngine.calculate_confidence(bank_txn)
            
      if confidence >= 80:
        SettlementMatch.objects.create(internal_transaction_id=bank_txn.reference_number, bank_transaction=bank_txn,
          match_confidence=confidence, status = 'matched')
        matched_count += 1
      else:
        SettlementMatch.objects.create(internal_transaction_id=bank_txn.reference_number, bank_transaction=bank_txn,
          match_confidence=confidence, status = 'unmatched')
    return matched_count
    
  @staticmethod
  def calculate_confidence(bank_txn):
    confidence = 0
    if bank_txn.reference_number:
      confidence += 40
    if bank_txn.amount > 0:
      confidence += 30
    if bank_txn.description:
      confidence += 30
        
    return confidence
    
  @staticmethod
  def flag_differences(statement_id):
    statement = BankStatement.objects.get(id=statement_id)
    unmatched = SettlementMatch.objects.filter(bank_transaction__statement=statement, status = 'unmatched')
    difference_count = 0
    for match in unmatched:
      SettlementDifference.objects.create(internal_transaction_id=match.internal_transaction_id, bank_transaction=match.bank_transaction,
        difference_amount=match.bank_transaction.amount, reason = 'no matching inter trans is pres.')
      difference_count += 1
        
    return difference_count

class SettlementService:
  @staticmethod
  def settlement_statement(statement_id):
    statement = BankStatement.objects.get(id=statement_id)
    statement.status = 'processing'
    statement.save()
    matched_count = MatchingEngine.auto_match(statement_id)
    difference_count = MatchingEngine.flag_differences(statement_id)
    statement.status = 'completed'
    statement.save()
    return {'matched_count': matched_count, 'difference_count': difference_count}
    
  @staticmethod
  def resolve_difference(difference_id, resolution):
    difference = SettlementDifference.objects.get(id=difference_id)
    difference.is_resolved = True
    difference.resolution_notes = resolution
    difference.save()
    return difference