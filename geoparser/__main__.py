import os
import sys
from appdirs import user_data_dir

def main():
    data_dir = user_data_dir('geoparser')
    db_path = os.path.join(data_dir, "geonames.db")

    if 'download' in sys.argv:
        if os.path.exists(db_path):
            user_input = input("GeoNames database found. Would you like to update the data? [y/n]: ")
            if user_input.lower() != 'y':
                return
            else:
                os.remove(db_path)

        from .downloader import main as download_main
        from .database import main as database_main

        download_main()
        database_main()

        for file_name in os.listdir(data_dir):
            if file_name.endswith('.txt'):
                os.remove(os.path.join(data_dir, file_name))
    else:
        print("Usage: python -m geoparser download")

if __name__ == '__main__':
    main()
