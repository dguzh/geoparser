from setuptools import setup, find_packages

setup(
    name='geoparser',
    version='0.1.6',
    author='Diego Gomes',
    author_email='diego.gomes@uzh.ch',
    packages=find_packages(),
    description='A geoparsing library for English texts',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'pandas',
        'numpy',
        'spacy',
        'sentence_transformers',
        'tqdm',
        'torch',
        'requests',
        'appdirs',
    ],
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
    ],
)
