from academics.models import Bulletin


class RankingService:

    @staticmethod
    def rank_classe(classe, periode):

        bulletins = Bulletin.objects.filter(
            eleve__classe=classe,
            periode=periode,
            actif=True
        ).order_by("-moyenne")

        rank = 0
        last_moyenne = None


        for index, b in enumerate(bulletins):

            if b.moyenne != last_moyenne:

                rank = index + 1

                last_moyenne = b.moyenne


            b.rang = rank

            b.save(update_fields=["rang"])
