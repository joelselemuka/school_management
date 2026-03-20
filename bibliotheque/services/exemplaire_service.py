from bibliotheque.models import Exemplaire

class ExemplaireService:
    @staticmethod
    def create_exemplaire(validated_data):
        return Exemplaire.objects.create(**validated_data)

    @staticmethod
    def update_exemplaire(exemplaire, validated_data):
        for attr, value in validated_data.items():
            setattr(exemplaire, attr, value)
        exemplaire.save()
        return exemplaire

    @staticmethod
    def get_all_actifs():
        return Exemplaire.objects.filter(actif=True)
