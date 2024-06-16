from setuptools import setup, find_packages

setup(
    name="geoparser",
    version="0.1.7",
    author="Diego Gomes",
    author_email="diego.gomes@uzh.ch",
    packages=find_packages(),
    description="A geoparsing library for English texts",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "numpy>=1.26.4",
        "pandas>=2.2.2",
        "spacy>=3.7.5",
        "sentence_transformers>=3.0.1",
        "tqdm>=4.66.4",
        "torch>=2.3.1",
        "requests>=2.32.3",
        "appdirs>=1.4.4",
        "datasets>=2.20.0",
        "haversine>=2.8.1",
        "accelerate>=0.31.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
    ],
)
