# Irchel Geoparser

[![CI](https://img.shields.io/github/actions/workflow/status/dguzh/geoparser/ci.yml?branch=main&logo=github&label=CI)](https://github.com/dguzh/geoparser/actions?query=event%3Apush+branch%3Amain+workflow%3ACI)
[![Tests](https://img.shields.io/github/actions/workflow/status/dguzh/geoparser/test.yml?branch=main&logo=github&label=tests)](https://github.com/dguzh/geoparser/actions/workflows/test.yml?query=branch%3Amain+)
[![Coverage](https://coverage-badge.samuelcolvin.workers.dev/dguzh/geoparser.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/dguzh/geoparser)
[![PyPI](https://img.shields.io/pypi/v/geoparser?&label=pypi%20package)](https://pypi.org/project/geoparser)
[![Python](https://img.shields.io/pypi/pyversions/geoparser)](https://pypi.org/project/geoparser)
[![License](https://img.shields.io/github/license/dguzh/geoparser)](https://github.com/dguzh/geoparser/blob/main/LICENSE)

A Python library for extracting place names from text and linking them to geographic locations.

## Features

- **Project-Based Workflows**: Store documents and results in a persistent database for long-term research
- **Modular Architecture**: Mix and match different recognizers and resolvers, or build your own
- **Trainable Models**: Fine-tune recognizers and resolvers on your own annotated data
- **Custom Gazetteers**: Integrate any geographic database through simple YAML configuration

## Installation

```bash
pip install geoparser
```

> **Note for macOS users**: The library requires SQLite extension support. Please see the [macOS setup guide](https://docs.geoparser.app/en/latest/macos.html) for installation instructions using Homebrew Python.

## Quick Start

```python
from geoparser import Geoparser

# Initialize with default settings
gp = Geoparser()

# Parse text
text = "Paris is the capital of France."
docs = gp.parse(text)

# Access results
for toponym in docs[0].toponyms:
    print(f"{toponym.text} -> {toponym.location.data}")
```

## Documentation

Full documentation is available at **[docs.geoparser.app](https://docs.geoparser.app)**

- [Installation Guide](https://docs.geoparser.app/en/latest/installation.html)
- [Quick Start Tutorial](https://docs.geoparser.app/en/latest/quickstart.html)
- [User Guides](https://docs.geoparser.app/en/latest/guides/projects.html)
- [API Reference](https://docs.geoparser.app/en/latest/api/geoparser.html)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgments

The Irchel Geoparser originated as part of my Master's thesis and was further developed with support from the [Department of Geography](https://www.geo.uzh.ch/) at the University of Zurich and the [Public Data Lab](https://publicdatalab.ch/) of the Digitalization Initiative of the Zurich Higher Education Institutions. I thank Prof. Dr. Ross Purves for the opportunity to continue this work as part of a research project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Third-party licenses are listed in [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).
