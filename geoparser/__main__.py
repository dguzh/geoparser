def main():
    import sys
    from .downloader import download

    if 'download' in sys.argv:
        download()
    else:
        print("Usage: python -m geoparser download")

if __name__ == '__main__':
    main()
    