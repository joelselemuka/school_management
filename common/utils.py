def get_jour_map():

    from core.models import SchoolConfiguration

    config = SchoolConfiguration.objects.filter(actif=True).first()

    if not config:
        raise ValueError("Configuration école manquante")

    if config.week_type == "ANGLAISE":
        return {
            "LUNDI": 0,
            "MARDI": 1,
            "MERCREDI": 2,
            "JEUDI": 3,
            "VENDREDI": 4,
        }

    # NORMALE
    return {
        "LUNDI": 0,
        "MARDI": 1,
        "MERCREDI": 2,
        "JEUDI": 3,
        "VENDREDI": 4,
        "SAMEDI": 5,
    }
