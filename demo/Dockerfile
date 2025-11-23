# Irchel Geoparser Demo - Docker Image
# This image provides a complete environment for running the "Around the World in Eighty Days" demo

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install geoparser and demo dependencies
RUN pip install --no-cache-dir geoparser jupyter plotly

# Download spaCy models
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download en_core_web_trf && \
    python -m spacy download xx_sent_ud_sm

# Pre-download and install GeoNames gazetteer
RUN python -m geoparser download geonames

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
