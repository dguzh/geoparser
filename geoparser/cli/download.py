from geoparser.constants import GAZETTEERS, GAZETTEERS_CHOICES


def download_cli(gazetteers: list[GAZETTEERS_CHOICES]):
    for gazetteer_name in gazetteers:
        gazetteer = GAZETTEERS[gazetteer_name]()
        gazetteer.setup_database()
