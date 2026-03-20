


from comptabilite.models.transaction import Transaction


class JournalService:

    @staticmethod
    def get_general_journal(date_from=None, date_to=None):

        qs = Transaction.objects.prefetch_related(
            "lines",
            "lines__account",
        ).order_by("created_at")

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        result = []

        for tx in qs:
            result.append({
                "reference": tx.reference,
                "date": tx.created_at,
                "description": tx.description,
                "lines": [
                    {
                        "account_code": line.account.code,
                        "account_name": line.account.name,
                        "debit": line.debit,
                        "credit": line.credit,
                    }
                    for line in tx.lines.all()
                ],
            })

        return result
