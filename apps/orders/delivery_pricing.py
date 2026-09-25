import math
from decimal import Decimal
from typing import Dict, Any, Optional

EARTH_RADIUS_KM = 6371.0
URBAN_FACTOR = 1.2  # Facteur de correction de distance urbaine (routes à Dakar)
AYYOU_SERVICE_FEE = Decimal('300.00')  # Surcoût fixe pour frais PayTech et commission AYYOU


def calculer_distance_haversine(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
    """
    Calcule la distance orthodromique en kilomètres entre deux points GPS
    en utilisant la formule d'Haversine avec ajustement urbain.
    """
    try:
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        delta_phi = math.radians(float(lat2) - float(lat1))
        delta_lambda = math.radians(float(lng2) - float(lng1))

        a = (
            math.sin(delta_phi / 2.0) ** 2 +
            math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance_directe = EARTH_RADIUS_KM * c

        # Distance estimée en réseau routier avec le facteur de correction urbain
        return round(distance_directe * URBAN_FACTOR, 2)
    except (TypeError, ValueError):
        return 0.0


def calculer_frais_livraison(
    etablissement: Any,
    latitude_client: Optional[float] = None,
    longitude_client: Optional[float] = None
) -> Dict[str, Any]:
    """
    Détermine les frais de livraison dynamiques en fonction de la géolocalisation
    du restaurant et du client.
    
    Grille tarifaire (Dakar & Banlieue) :
    - 0 à 3 km : 1 000 FCFA (livreur) + 300 FCFA (AYYOU) = 1 300 FCFA
    - 3.1 à 7 km : 1 500 FCFA (livreur) + 300 FCFA (AYYOU) = 1 800 FCFA
    - 7.1 à 12 km : 2 000 FCFA (livreur) + 300 FCFA (AYYOU) = 2 300 FCFA
    - 12.1 à 20 km : 3 000 FCFA (livreur) + 300 FCFA (AYYOU) = 3 300 FCFA
    - > 20 km : 4 000 FCFA (livreur) + 300 FCFA (AYYOU) = 4 300 FCFA
    """
    lat_etab = getattr(etablissement, 'latitude', None)
    lng_etab = getattr(etablissement, 'longitude', None)

    if (lat_etab is None or lng_etab is None) and etablissement:
        addr = f"{getattr(etablissement, 'adresse', '')} {getattr(etablissement, 'nom', '')}".lower()
        if 'keur massar' in addr:
            lat_etab, lng_etab = 14.7770, -17.3117
        elif 'almadies' in addr:
            lat_etab, lng_etab = 14.7450, -17.5150
        elif 'ouakam' in addr:
            lat_etab, lng_etab = 14.7250, -17.4850
        elif 'mermoz' in addr:
            lat_etab, lng_etab = 14.7050, -17.4700
        elif 'fann' in addr:
            lat_etab, lng_etab = 14.6850, -17.4650
        elif 'hlm' in addr:
            lat_etab, lng_etab = 14.7100, -17.4450
        elif 'plateau' in addr or 'dakar' in addr:
            lat_etab, lng_etab = 14.6698, -17.4381

    distance_km = 0.0
    if lat_etab is not None and lng_etab is not None and latitude_client is not None and longitude_client is not None:
        distance_km = calculer_distance_haversine(lat_etab, lng_etab, latitude_client, longitude_client)

    # Application de la grille par kilomètres
    if distance_km <= 0.0:
        frais_livreur_net = Decimal('1000.00')
    elif distance_km <= 3.0:
        frais_livreur_net = Decimal('1000.00')
    elif distance_km <= 7.0:
        frais_livreur_net = Decimal('1500.00')
    elif distance_km <= 12.0:
        frais_livreur_net = Decimal('2000.00')
    elif distance_km <= 20.0:
        frais_livreur_net = Decimal('3000.00')
    else:
        frais_livreur_net = Decimal('4000.00')

    frais_livraison_client = frais_livreur_net + AYYOU_SERVICE_FEE

    return {
        'distance_km': distance_km,
        'frais_livreur_net': frais_livreur_net,
        'majoration_ayyou': AYYOU_SERVICE_FEE,
        'frais_livraison_client': frais_livraison_client
    }
