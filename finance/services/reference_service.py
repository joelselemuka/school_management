from django.utils import timezone
import uuid


class ReferenceService:

    @staticmethod
    def generate(prefix):

        date = timezone.now().strftime("%Y%m%d")

        uid = uuid.uuid4().hex[:6].upper()

        return f"{prefix}-{date}-{uid}"
