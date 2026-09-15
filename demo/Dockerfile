# Irchel Geoparser Demo - Docker Image
# This image provides a complete environment for running the "Around the World in Eighty Days" demo

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install geoparser and demo dependencies. The notebook uses en_core_web_trf, whose
# first component comes from the curated_transformer factory in spacy-curated-transformers
# rather than from spaCy itself; without it the model cannot be loaded. The bound is the
# one the model declares — unpinned, pip installs the 2.x line, which is built for a
# later spaCy generation than the one geoparser uses.
RUN pip install --no-cache-dir geoparser jupyter plotly \
    "spacy-curated-transformers>=0.2.2,<1.0.0"

# Download spaCy models
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download en_core_web_trf && \
    python -m spacy download xx_sent_ud_sm

# Pre-install GeoNames gazetteer
RUN python -m geoparser install geonames

# Create workspace directory
WORKDIR /workspace

# Copy the demo notebook
COPY demo/demo.ipynb /workspace/

# Expose Jupyter port
EXPOSE 8888

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Start JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--LabApp.token=", "--LabApp.password="]
