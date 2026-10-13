from django.contrib import admin

from .models import Account, CashMovement, Creditor, CreditorComment, CreditorTransaction, Exchange, Expense, Payment, Transfer

for m in [Account, CashMovement, Payment, Transfer, Exchange, Expense, Creditor, CreditorTransaction, CreditorComment]:
    admin.site.register(m)
