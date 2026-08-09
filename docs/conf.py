# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Irchel Geoparser"
copyright = "2024-2026, Diego Gomes"
author = "Diego Gomes"

# Read from pyproject.toml rather than importlib.metadata, because Read the Docs
# installs the dependencies with --no-root and never installs geoparser itself.
_pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
release = tomllib.loads(_pyproject.read_text(encoding="utf-8"))["tool"]["poetry"][
    "version"
]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_tabs.tabs",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

add_module_names = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_show_sourcelink = False
