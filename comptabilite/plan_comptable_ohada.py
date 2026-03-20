"""
Plan Comptable OHADA (Organisation pour l'Harmonisation en Afrique du Droit des Affaires)
adapté pour une école.

Classes de comptes:
- Classe 1: Comptes de ressources durables (Capital, Réserves, Dettes long terme)
- Classe 2: Comptes d'actif immobilisé (Immobilisations)
- Classe 3: Comptes de stocks
- Classe 4: Comptes de tiers (Créances, Dettes)
- Classe 5: Comptes de trésorerie (Banque, Caisse)
- Classe 6: Comptes de charges
- Classe 7: Comptes de produits
- Classe 8: Comptes spéciaux
"""

PLAN_COMPTABLE_OHADA_ECOLE = {
    # ========================================
    # CLASSE 1: COMPTES DE RESSOURCES DURABLES
    # ========================================
    '101': {'nom': 'Capital social', 'type': 'equity'},
    '1013': {'nom': 'Capital souscrit, appelé, versé', 'type': 'equity'},
    
    '106': {'nom': 'Réserves', 'type': 'equity'},
    '1061': {'nom': 'Réserve légale', 'type': 'equity'},
    '1063': {'nom': 'Réserves statutaires', 'type': 'equity'},
    '1068': {'nom': 'Autres réserves', 'type': 'equity'},
    
    '11': {'nom': 'Report à nouveau', 'type': 'equity'},
    '110': {'nom': 'Report à nouveau créditeur', 'type': 'equity'},
    '119': {'nom': 'Report à nouveau débiteur', 'type': 'equity'},
    
    '12': {'nom': 'Résultat de l\'exercice', 'type': 'equity'},
    '121': {'nom': 'Bénéfice', 'type': 'equity'},
    '129': {'nom': 'Perte', 'type': 'equity'},
    
    '16': {'nom': 'Emprunts et dettes assimilées', 'type': 'liability'},
    '161': {'nom': 'Emprunts obligataires', 'type': 'liability'},
    '162': {'nom': 'Emprunts auprès des établissements de crédit', 'type': 'liability'},
    '164': {'nom': 'Emprunts et dettes auprès des associés', 'type': 'liability'},
    '165': {'nom': 'Dépôts et cautionnements reçus', 'type': 'liability'},
    '168': {'nom': 'Autres emprunts et dettes', 'type': 'liability'},
    
    '17': {'nom': 'Dettes de location-acquisition', 'type': 'liability'},
    
    # ========================================
    # CLASSE 2: COMPTES D'ACTIF IMMOBILISÉ
    # ========================================
    
    # Immobilisations incorporelles
    '201': {'nom': 'Frais d\'établissement', 'type': 'asset'},
    '211': {'nom': 'Terrains', 'type': 'asset'},
    '212': {'nom': 'Agencements et aménagements de terrains', 'type': 'asset'},
    '213': {'nom': 'Constructions sur sol propre', 'type': 'asset'},
    '214': {'nom': 'Constructions sur sol d\'autrui', 'type': 'asset'},
    '215': {'nom': 'Installations techniques', 'type': 'asset'},
    '218': {'nom': 'Autres installations et agencements', 'type': 'asset'},
    
    # Matériel
    '221': {'nom': 'Matériel et outillage industriel et commercial', 'type': 'asset'},
    '222': {'nom': 'Matériel et outillage', 'type': 'asset'},
    '223': {'nom': 'Matériel d\'enseignement', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '224': {'nom': 'Mobilier scolaire', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '228': {'nom': 'Installations générales, agencements', 'type': 'asset'},
    
    '231': {'nom': 'Bâtiments administratifs et commerciaux', 'type': 'asset'},
    '232': {'nom': 'Bâtiments scolaires', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '233': {'nom': 'Ouvrages d\'infrastructure', 'type': 'asset'},
    
    '241': {'nom': 'Matériel de transport', 'type': 'asset'},
    '2411': {'nom': 'Véhicules de transport scolaire', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '2415': {'nom': 'Matériel automobile', 'type': 'asset'},
    
    '244': {'nom': 'Matériel mobilier', 'type': 'asset'},
    '245': {'nom': 'Matériel de bureau', 'type': 'asset'},
    '2451': {'nom': 'Mobilier de bureau', 'type': 'asset'},
    '2454': {'nom': 'Matériel informatique', 'type': 'asset'},
    '2455': {'nom': 'Matériel de télécommunication', 'type': 'asset'},
    
    '246': {'nom': 'Emballages récupérables', 'type': 'asset'},
    
    # Immobilisations financières
    '26': {'nom': 'Titres de participation', 'type': 'asset'},
    '261': {'nom': 'Titres de participation', 'type': 'asset'},
    '27': {'nom': 'Autres immobilisations financières', 'type': 'asset'},
    '271': {'nom': 'Prêts et créances', 'type': 'asset'},
    '275': {'nom': 'Dépôts et cautionnements versés', 'type': 'asset'},
    
    # Amortissements
    '281': {'nom': 'Amortissements des immobilisations incorporelles', 'type': 'asset'},
    '282': {'nom': 'Amortissements des terrains', 'type': 'asset'},
    '283': {'nom': 'Amortissements des bâtiments', 'type': 'asset'},
    '284': {'nom': 'Amortissements du matériel', 'type': 'asset'},
    
    # ========================================
    # CLASSE 3: COMPTES DE STOCKS
    # ========================================
    '31': {'nom': 'Marchandises', 'type': 'asset'},
    '32': {'nom': 'Matières premières et fournitures', 'type': 'asset'},
    '321': {'nom': 'Fournitures scolaires', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '322': {'nom': 'Fournitures de bureau', 'type': 'asset'},
    '323': {'nom': 'Fournitures d\'entretien', 'type': 'asset'},
    
    '33': {'nom': 'Autres approvisionnements', 'type': 'asset'},
    '38': {'nom': 'Stocks en cours de route', 'type': 'asset'},
    '39': {'nom': 'Dépréciations des stocks', 'type': 'asset'},
    
    # ========================================
    # CLASSE 4: COMPTES DE TIERS
    # ========================================
    
    # Fournisseurs
    '401': {'nom': 'Fournisseurs - Dettes en compte', 'type': 'liability'},
    '4011': {'nom': 'Fournisseurs', 'type': 'liability'},
    '4017': {'nom': 'Fournisseurs - Retenues de garantie', 'type': 'liability'},
    '404': {'nom': 'Fournisseurs d\'immobilisations', 'type': 'liability'},
    '408': {'nom': 'Fournisseurs - Factures non parvenues', 'type': 'liability'},
    
    # Clients (Familles/Parents d'élèves pour une école)
    '411': {'nom': 'Clients', 'type': 'asset'},
    '4111': {'nom': 'Parents d\'élèves', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '4112': {'nom': 'Frais de scolarité à recevoir', 'type': 'asset'},  # SPÉCIFIQUE ÉCOLE
    '416': {'nom': 'Clients douteux', 'type': 'asset'},
    '418': {'nom': 'Clients - Produits à recevoir', 'type': 'asset'},
    '419': {'nom': 'Clients créditeurs', 'type': 'liability'},
    
    # Personnel
    '421': {'nom': 'Personnel - Avances et acomptes', 'type': 'asset'},
    '422': {'nom': 'Enseignants - Rémunérations dues', 'type': 'liability'},  # SPÉCIFIQUE ÉCOLE
    '423': {'nom': 'Personnel administratif - Rémunérations dues', 'type': 'liability'},
    '424': {'nom': 'Personnel de service - Rémunérations dues', 'type': 'liability'},
    '425': {'nom': 'Personnel - Avances', 'type': 'liability'},
    '426': {'nom': 'Personnel - Dépôts', 'type': 'liability'},
    '427': {'nom': 'Personnel - Oppositions', 'type': 'liability'},
    '428': {'nom': 'Personnel - Charges à payer', 'type': 'liability'},
    
    # Sécurité sociale
    '431': {'nom': 'Sécurité sociale', 'type': 'liability'},
    '432': {'nom': 'Autres organismes sociaux', 'type': 'liability'},
    
    # État
    '441': {'nom': 'État - Impôt sur les bénéfices', 'type': 'liability'},
    '442': {'nom': 'État - Autres impôts et taxes', 'type': 'liability'},
    '443': {'nom': 'Opérations particulières avec l\'État', 'type': 'liability'},
    '444': {'nom': 'État - Impôts sur le chiffre d\'affaires', 'type': 'liability'},
    '445': {'nom': 'État - Taxes sur le chiffre d\'affaires', 'type': 'liability'},
    '446': {'nom': 'Organismes internationaux', 'type': 'liability'},
    '447': {'nom': 'État - Autres impôts, taxes et versements assimilés', 'type': 'liability'},
    '448': {'nom': 'État - Charges à payer', 'type': 'liability'},
    '449': {'nom': 'État - Produits à recevoir', 'type': 'asset'},
    
    # Associés et groupe
    '45': {'nom': 'Associés et groupe', 'type': 'liability'},
    '451': {'nom': 'Associés - Comptes courants', 'type': 'liability'},
    '455': {'nom': 'Associés - Dividendes à payer', 'type': 'liability'},
    
    # Débiteurs et créditeurs divers
    '461': {'nom': 'Créances sur cessions d\'immobilisations', 'type': 'asset'},
    '462': {'nom': 'Créances sur cessions de titres', 'type': 'asset'},
    '465': {'nom': 'Créances sur cessions de valeurs mobilières de placement', 'type': 'asset'},
    '467': {'nom': 'Autres comptes débiteurs ou créditeurs', 'type': 'asset'},
    '471': {'nom': 'Comptes d\'attente', 'type': 'asset'},
    '472': {'nom': 'Comptes d\'attente créditeurs', 'type': 'liability'},
    '475': {'nom': 'Créditeurs divers', 'type': 'liability'},
    '476': {'nom': 'Charges constatées d\'avance', 'type': 'asset'},
    '477': {'nom': 'Produits constatés d\'avance', 'type': 'liability'},
    
    # Comptes de régularisation
    '481': {'nom': 'Comptes de répartition périodique des charges', 'type': 'asset'},
    '486': {'nom': 'Charges constatées d\'avance', 'type': 'asset'},
    '487': {'nom': 'Produits constatés d\'avance', 'type': 'liability'},
    
    '491': {'nom': 'Dépréciation des comptes de clients', 'type': 'asset'},
    
    # ========================================
    # CLASSE 5: COMPTES DE TRÉSORERIE
    # ========================================
    
    # Titres de placement
    '50': {'nom': 'Titres de placement', 'type': 'asset'},
    '501': {'nom': 'Parts dans les entreprises liées', 'type': 'asset'},
    '502': {'nom': 'Actions propres', 'type': 'asset'},
    '503': {'nom': 'Actions', 'type': 'asset'},
    '504': {'nom': 'Autres titres conférant un droit de propriété', 'type': 'asset'},
    '506': {'nom': 'Obligations', 'type': 'asset'},
    '507': {'nom': 'Bons du Trésor et bons de caisse à court terme', 'type': 'asset'},
    
    # Banques
    '52': {'nom': 'Banques', 'type': 'asset'},
    '521': {'nom': 'Banques locales', 'type': 'asset'},
    '522': {'nom': 'Banques autres', 'type': 'asset'},
    
    # Établissements financiers et assimilés
    '53': {'nom': 'Établissements financiers et assimilés', 'type': 'asset'},
    '531': {'nom': 'Chèques postaux', 'type': 'asset'},
    '532': {'nom': 'Trésor', 'type': 'asset'},
    '533': {'nom': 'Banques', 'type': 'asset'},
    
    # Caisse
    '57': {'nom': 'Caisse', 'type': 'asset'},
    '571': {'nom': 'Caisse siège social', 'type': 'asset'},
    '572': {'nom': 'Caisse succursale', 'type': 'asset'},
    '573': {'nom': 'Caisse en devises', 'type': 'asset'},
    
    # Régies d'avances et accréditifs
    '58': {'nom': 'Régies d\'avances, accréditifs et virements internes', 'type': 'asset'},
    '581': {'nom': 'Régies d\'avances', 'type': 'asset'},
    '582': {'nom': 'Accréditifs', 'type': 'asset'},
    '585': {'nom': 'Virements de fonds', 'type': 'asset'},
    
    # Dépréciations et risques provisionnés
    '59': {'nom': 'Dépréciation des comptes de trésorerie', 'type': 'asset'},
    '590': {'nom': 'Dépréciation des titres de placement', 'type': 'asset'},
    '599': {'nom': 'Risques provisionnés sur opérations de trésorerie', 'type': 'liability'},
    
    # ========================================
    # CLASSE 6: COMPTES DE CHARGES
    # ========================================
    
    # Achats
    '60': {'nom': 'Achats et variations des stocks', 'type': 'expense'},
    '601': {'nom': 'Achats de marchandises', 'type': 'expense'},
    '602': {'nom': 'Achats de matières premières et fournitures liées', 'type': 'expense'},
    '6021': {'nom': 'Achats de fournitures scolaires', 'type': 'expense'},  # SPÉCIFIQUE ÉCOLE
    '603': {'nom': 'Variations des stocks de biens achetés', 'type': 'expense'},
    '604': {'nom': 'Achats stockés - Matières et fournitures', 'type': 'expense'},
    '605': {'nom': 'Autres achats', 'type': 'expense'},
    '608': {'nom': 'Achats d\'emballages', 'type': 'expense'},
    
    # Services extérieurs
    '61': {'nom': 'Transports', 'type': 'expense'},
    '611': {'nom': 'Transports sur achats', 'type': 'expense'},
    '612': {'nom': 'Transports sur ventes', 'type': 'expense'},
    '613': {'nom': 'Transports pour le compte de tiers', 'type': 'expense'},
    '614': {'nom': 'Transports du personnel', 'type': 'expense'},
    '616': {'nom': 'Transports scolaires', 'type': 'expense'},  # SPÉCIFIQUE ÉCOLE
    '618': {'nom': 'Autres frais de transport', 'type': 'expense'},
    
    '62': {'nom': 'Autres services extérieurs A', 'type': 'expense'},
    '621': {'nom': 'Sous-traitance générale', 'type': 'expense'},
    '622': {'nom': 'Locations et charges locatives', 'type': 'expense'},
    '6221': {'nom': 'Locations de terrains', 'type': 'expense'},
    '6222': {'nom': 'Locations de bâtiments', 'type': 'expense'},
    '6223': {'nom': 'Locations de matériel et d\'outillage', 'type': 'expense'},
    '6224': {'nom': 'Locations de mobilier et matériel de bureau', 'type': 'expense'},
    '6225': {'nom': 'Locations de matériel informatique', 'type': 'expense'},
    '6226': {'nom': 'Locations de matériel de transport', 'type': 'expense'},
    '623': {'nom': 'Redevances de crédit-bail', 'type': 'expense'},
    '624': {'nom': 'Entretien, réparations et maintenance', 'type': 'expense'},
    '6241': {'nom': 'Entretien et réparations des biens immobiliers', 'type': 'expense'},
    '6242': {'nom': 'Entretien et réparations des biens mobiliers', 'type': 'expense'},
    '6243': {'nom': 'Maintenance', 'type': 'expense'},
    '625': {'nom': 'Primes d\'assurances', 'type': 'expense'},
    '626': {'nom': 'Études, recherches et documentation', 'type': 'expense'},
    '627': {'nom': 'Publicité, publications, relations publiques', 'type': 'expense'},
    '628': {'nom': 'Frais de télécommunications', 'type': 'expense'},
    
    '63': {'nom': 'Autres services extérieurs B', 'type': 'expense'},
    '631': {'nom': 'Frais bancaires', 'type': 'expense'},
    '632': {'nom': 'Rémunérations d\'intermédiaires et de conseils', 'type': 'expense'},
    '633': {'nom': 'Frais de formation du personnel', 'type': 'expense'},
    '634': {'nom': 'Redevances pour brevets, licences, logiciels', 'type': 'expense'},
    '635': {'nom': 'Cotisations', 'type': 'expense'},
    '637': {'nom': 'Rémunérations du personnel extérieur', 'type': 'expense'},
    '638': {'nom': 'Autres charges externes', 'type': 'expense'},
    
    # Impôts et taxes
    '64': {'nom': 'Impôts et taxes', 'type': 'expense'},
    '641': {'nom': 'Impôts et taxes directs', 'type': 'expense'},
    '645': {'nom': 'Impôts et taxes indirects', 'type': 'expense'},
    '646': {'nom': 'Droits d\'enregistrement', 'type': 'expense'},
    '647': {'nom': 'Pénalités et amendes fiscales', 'type': 'expense'},
    
    # Autres charges
    '65': {'nom': 'Autres charges', 'type': 'expense'},
    '651': {'nom': 'Redevances pour concessions, brevets', 'type': 'expense'},
    '652': {'nom': 'Moins-values sur sortie d\'actifs immobilisés', 'type': 'expense'},
    '653': {'nom': 'Jetons de présence', 'type': 'expense'},
    '654': {'nom': 'Pertes sur créances', 'type': 'expense'},
    '658': {'nom': 'Charges diverses', 'type': 'expense'},
    
    # Charges de personnel
    '66': {'nom': 'Charges de personnel', 'type': 'expense'},
    '661': {'nom': 'Rémunérations directes versées au personnel national', 'type': 'expense'},
    '6611': {'nom': 'Appointements salaires et commissions', 'type': 'expense'},
    '6612': {'nom': 'Primes et gratifications', 'type': 'expense'},
    '6613': {'nom': 'Congés payés', 'type': 'expense'},
    '6614': {'nom': 'Indemnités de préavis, de licenciement et de recherche d\'embauche', 'type': 'expense'},
    '6615': {'nom': 'Indemnités de maladie versées aux travailleurs', 'type': 'expense'},
    '6616': {'nom': 'Supplément familial', 'type': 'expense'},
    '6617': {'nom': 'Avantages en nature', 'type': 'expense'},
    '6618': {'nom': 'Autres rémunérations directes', 'type': 'expense'},
    
    '662': {'nom': 'Rémunérations enseignants', 'type': 'expense'},  # SPÉCIFIQUE ÉCOLE
    '6621': {'nom': 'Salaires enseignants permanents', 'type': 'expense'},
    '6622': {'nom': 'Salaires enseignants vacataires', 'type': 'expense'},
    '6623': {'nom': 'Primes et indemnités enseignants', 'type': 'expense'},
    
    '663': {'nom': 'Rémunérations personnel administratif', 'type': 'expense'},  # SPÉCIFIQUE ÉCOLE
    '664': {'nom': 'Rémunérations personnel de service', 'type': 'expense'},  # SPÉCIFIQUE ÉCOLE
    
    '665': {'nom': 'Rémunérations occasionnelles du personnel', 'type': 'expense'},
    '666': {'nom': 'Charges sociales', 'type': 'expense'},
    '6661': {'nom': 'Charges sociales sur rémunérations', 'type': 'expense'},
    '6662': {'nom': 'Charges sociales sur congés payés', 'type': 'expense'},
    '6663': {'nom': 'Charges sociales sur indemnités', 'type': 'expense'},
    '6664': {'nom': 'Charges sociales sur avantages en nature', 'type': 'expense'},
    '6665': {'nom': 'Charges sociales sur primes et gratifications', 'type': 'expense'},
    '6668': {'nom': 'Autres charges sociales', 'type': 'expense'},
    
    '667': {'nom': 'Rémunérations transférées', 'type': 'expense'},
    '668': {'nom': 'Autres charges sociales', 'type': 'expense'},
    
    # Frais financiers
    '67': {'nom': 'Frais financiers et charges assimilées', 'type': 'expense'},
    '671': {'nom': 'Intérêts des emprunts', 'type': 'expense'},
    '672': {'nom': 'Intérêts dans loyers de crédit-bail', 'type': 'expense'},
    '673': {'nom': 'Escomptes accordés', 'type': 'expense'},
    '674': {'nom': 'Autres intérêts', 'type': 'expense'},
    '676': {'nom': 'Pertes de change', 'type': 'expense'},
    '677': {'nom': 'Pertes sur cessions de titres de placement', 'type': 'expense'},
    '678': {'nom': 'Autres charges financières', 'type': 'expense'},
    
    # Dotations aux amortissements
    '68': {'nom': 'Dotations aux amortissements', 'type': 'expense'},
    '681': {'nom': 'Dotations aux amortissements d\'exploitation', 'type': 'expense'},
    '6811': {'nom': 'Dotations aux amortissements des charges immobilisées', 'type': 'expense'},
    '6812': {'nom': 'Dotations aux amortissements des immobilisations incorporelles', 'type': 'expense'},
    '6813': {'nom': 'Dotations aux amortissements des immobilisations corporelles', 'type': 'expense'},
    
    '686': {'nom': 'Dotations aux provisions pour risques et charges', 'type': 'expense'},
    '687': {'nom': 'Dotations aux provisions financières', 'type': 'expense'},
    '688': {'nom': 'Dotations aux autres provisions', 'type': 'expense'},
    '689': {'nom': 'Dotations aux amortissements des charges à répartir', 'type': 'expense'},
    
    # ========================================
    # CLASSE 7: COMPTES DE PRODUITS
    # ========================================
    
    # Ventes
    '70': {'nom': 'Ventes de produits fabriqués, prestations de services', 'type': 'income'},
    '701': {'nom': 'Ventes de produits finis', 'type': 'income'},
    '7011': {'nom': 'Frais de scolarité', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE (PRINCIPAL)
    '7012': {'nom': 'Frais d\'inscription', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7013': {'nom': 'Frais de réinscription', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7014': {'nom': 'Frais d\'examen', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    
    '702': {'nom': 'Ventes de produits intermédiaires', 'type': 'income'},
    '703': {'nom': 'Ventes de produits résiduels', 'type': 'income'},
    '704': {'nom': 'Travaux', 'type': 'income'},
    '705': {'nom': 'Études', 'type': 'income'},
    
    '706': {'nom': 'Autres prestations de services', 'type': 'income'},
    '7061': {'nom': 'Services de cantine', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7062': {'nom': 'Services de transport', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7063': {'nom': 'Services d\'internat', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7064': {'nom': 'Activités extra-scolaires', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    '7065': {'nom': 'Location de locaux', 'type': 'income'},
    '7066': {'nom': 'Vente de fournitures scolaires', 'type': 'income'},  # SPÉCIFIQUE ÉCOLE
    
    '707': {'nom': 'Produits accessoires', 'type': 'income'},
    '7071': {'nom': 'Produits des services exploités dans l\'intérêt du personnel', 'type': 'income'},
    '7072': {'nom': 'Commissions et courtages', 'type': 'income'},
    '7073': {'nom': 'Locations diverses', 'type': 'income'},
    '7074': {'nom': 'Bonis sur reprises d\'emballages', 'type': 'income'},
    '7075': {'nom': 'Ports et frais accessoires facturés', 'type': 'income'},
    '7076': {'nom': 'Bonis sur travaux', 'type': 'income'},
    '7077': {'nom': 'Produits de services annexes', 'type': 'income'},
    '7078': {'nom': 'Autres produits accessoires', 'type': 'income'},
    
    '708': {'nom': 'Produits des activités annexes', 'type': 'income'},
    
    # Subventions d'exploitation
    '71': {'nom': 'Subventions d\'exploitation', 'type': 'income'},
    '711': {'nom': 'Subventions d\'équilibre', 'type': 'income'},
    '712': {'nom': 'Subventions publiques', 'type': 'income'},  # IMPORTANT pour écoles
    '713': {'nom': 'Subventions d\'organisations internationales', 'type': 'income'},
    '718': {'nom': 'Autres subventions d\'exploitation', 'type': 'income'},
    
    # Production immobilisée
    '72': {'nom': 'Production immobilisée', 'type': 'income'},
    '721': {'nom': 'Immobilisations incorporelles', 'type': 'income'},
    '722': {'nom': 'Immobilisations corporelles', 'type': 'income'},
    '726': {'nom': 'Immobilisations financières', 'type': 'income'},
    
    # Variations des stocks
    '73': {'nom': 'Variations des stocks de biens et services produits', 'type': 'income'},
    '734': {'nom': 'Variations des en-cours', 'type': 'income'},
    '735': {'nom': 'Variations des stocks de produits', 'type': 'income'},
    
    # Autres produits
    '75': {'nom': 'Autres produits', 'type': 'income'},
    '752': {'nom': 'Revenus des immeubles non affectés aux activités professionnelles', 'type': 'income'},
    '753': {'nom': 'Jetons de présence et autres rémunérations d\'administrateurs', 'type': 'income'},
    '754': {'nom': 'Ristournes perçues des coopératives', 'type': 'income'},
    '755': {'nom': 'Quotes-parts de résultat sur opérations faites en commun', 'type': 'income'},
    '758': {'nom': 'Produits divers', 'type': 'income'},
    '7581': {'nom': 'Dons et libéralités reçus', 'type': 'income'},  # IMPORTANT pour écoles
    '7582': {'nom': 'Legs et donations', 'type': 'income'},
    
    # Reprises de charges
    '76': {'nom': 'Reprises de charges', 'type': 'income'},
    '761': {'nom': 'Reprises de provisions d\'exploitation', 'type': 'income'},
    '762': {'nom': 'Reprises de provisions financières', 'type': 'income'},
    
    # Produits financiers
    '77': {'nom': 'Revenus financiers et produits assimilés', 'type': 'income'},
    '771': {'nom': 'Intérêts de prêts', 'type': 'income'},
    '772': {'nom': 'Revenus de participations', 'type': 'income'},
    '773': {'nom': 'Escomptes obtenus', 'type': 'income'},
    '774': {'nom': 'Revenus des titres de placement', 'type': 'income'},
    '776': {'nom': 'Gains de change', 'type': 'income'},
    '777': {'nom': 'Gains sur cessions de titres de placement', 'type': 'income'},
    '778': {'nom': 'Autres produits financiers', 'type': 'income'},
    
    # Transferts de charges
    '78': {'nom': 'Transferts de charges', 'type': 'income'},
    '781': {'nom': 'Transferts de charges d\'exploitation', 'type': 'income'},
    '787': {'nom': 'Transferts de charges financières', 'type': 'income'},
    
    # ========================================
    # CLASSE 8: COMPTES SPÉCIAUX
    # ========================================
    '80': {'nom': 'Engagements', 'type': 'equity'},
    '81': {'nom': 'Valeurs à l\'encaissement', 'type': 'asset'},
    '82': {'nom': 'Dettes rattachées à des participations', 'type': 'liability'},
    '83': {'nom': 'Engagements hors bilan', 'type': 'equity'},
    '84': {'nom': 'Produits hors activités ordinaires', 'type': 'income'},
    '85': {'nom': 'Charges hors activités ordinaires', 'type': 'expense'},
    '86': {'nom': 'Comptes de liaison', 'type': 'equity'},
    '87': {'nom': 'Comptes de synthèse', 'type': 'equity'},
    '88': {'nom': 'Résultat', 'type': 'equity'},
}


def get_plan_comptable_par_type(type_compte):
    """
    Retourne tous les comptes d'un type donné.
    
    Args:
        type_compte: asset, liability, equity, income, expense
        
    Returns:
        dict: Comptes filtrés
    """
    return {
        code: info 
        for code, info in PLAN_COMPTABLE_OHADA_ECOLE.items() 
        if info['type'] == type_compte
    }


def get_comptes_specifiques_ecole():
    """
    Retourne les comptes spécifiques adaptés aux écoles.
    """
    comptes_ecole = {}
    for code, info in PLAN_COMPTABLE_OHADA_ECOLE.items():
        if '# SPÉCIFIQUE ÉCOLE' in str(info):
            comptes_ecole[code] = info
    return comptes_ecole


def creer_comptes_depuis_plan():
    """
    Crée tous les comptes du plan comptable dans la base de données.
    Utiliser avec: python manage.py shell
    
    Usage:
        from comptabilite.plan_comptable_ohada import creer_comptes_depuis_plan
        creer_comptes_depuis_plan()
    """
    from comptabilite.models import Account
    
    created_count = 0
    updated_count = 0
    
    for code, info in PLAN_COMPTABLE_OHADA_ECOLE.items():
        account, created = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': info['nom'],
                'type': info['type']
            }
        )
        
        if created:
            created_count += 1
        else:
            # Mise à jour si nécessaire
            account.name = info['nom']
            account.type = info['type']
            account.save()
            updated_count += 1
    
    return {
        'created': created_count,
        'updated': updated_count,
        'total': created_count + updated_count
    }
