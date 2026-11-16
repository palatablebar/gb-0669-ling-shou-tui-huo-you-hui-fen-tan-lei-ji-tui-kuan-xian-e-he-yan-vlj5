from decimal import Decimal

def amount(cents):return format(Decimal(cents)/100,'.2f')
