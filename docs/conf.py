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
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_tabs.tabs",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable", None),
}

# Output blocks are nothing to copy, so keep the button off them. Everything else keeps the
# extension's default target, a `pre` inside a highlighted block.
copybutton_selector = "div:not(.highlight-text) > div.highlight > pre"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

add_module_names = False

# Internal base classes that appear in autodoc signatures but are not part of the
# documented surface, so there is nothing to link them to.
nitpick_ignore = [
    ("py:class", "geoparser.modules.module.Module"),
    # Shapely does not publish this base class in its objects.inventory.
    ("py:class", "shapely.geometry.base.BaseGeometry"),
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_static_path = ["_static"]

html_logo = "_static/logo.png"
html_favicon = "_static/favicon.ico"
html_css_files = ["custom.css"]
html_show_sourcelink = False

html_theme_options = {
    # Radix "cyan" is within a shade of the logo's teal, so no CSS override is needed.
    "accent_color": "cyan",
    "github_url": "https://github.com/dguzh/geoparser",
    "og_image_url": "https://docs.geoparser.app/en/latest/_static/og-image.png",
    # The theme reserves a sidebar slot for Read the Docs ads by default.
    "ethical_ads_publisher": "",
}

# Drives the repository link in the sidebar and the "Edit this page" links. The theme's
# defaults for the branch and the docs directory (main, /docs/) already match this repo.
html_context = {
    "source_type": "github",
    "source_user": "dguzh",
    "source_repo": "geoparser",
}
