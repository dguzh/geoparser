# Irchel Geoparser Demo

This demo showcases the Irchel Geoparser by extracting and mapping place names mentioned in Jules Verne's "Around the World in Eighty Days".

## Running the Demo

Simply run this single Docker command:

```bash
docker run -p 8888:8888 dguzh/geoparser-demo:latest
```

**Note**: The first time you run this command, it will take approximately 5 minutes to download the Docker image (compressed to ~10 GB, expands to ~30 GB). Subsequent runs will be instant.

Once the container starts, open your browser to `http://localhost:8888` and open the `demo.ipynb` notebook.

For more information, see the [Demo](https://docs.geoparser.app/en/latest/demo.html) page in the documentation.
