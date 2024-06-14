import sys
from importlib import import_module

GAZETTEERS = {
    'geonames': 'geonames.GeoNames'
}

def main():
    if len(sys.argv) == 3 and sys.argv[1] == 'download':
        gazetteer_name = sys.argv[2].lower()
        if gazetteer_name in GAZETTEERS:
            gazetteer_module, gazetteer_class = GAZETTEERS[gazetteer_name].split('.')
            
            module = import_module('.' + gazetteer_module, package='geoparser')
            gazetteer = getattr(module, gazetteer_class)()

            gazetteer.setup_database()

        else:
            available = ", ".join(GAZETTEERS.keys())
            print(f"Invalid gazetteer name. Available gazetteers: {available}")
    else:
        print("Usage: python -m geoparser download [gazetteer_name]")

if __name__ == '__main__':
    main()
