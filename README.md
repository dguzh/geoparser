# Irchel Geoparser

[![CI](https://img.shields.io/github/actions/workflow/status/dguzh/geoparser/test.yml?branch=main&logo=github&label=CI)](https://github.com/dguzh/geoparser/actions/workflows/test.yml?query=branch%3Amain+)
[![Coverage](https://coverage-badge.samuelcolvin.workers.dev/dguzh/geoparser.svg)](https://coverage-badge.samuelcolvin.workers.dev/redirect/dguzh/geoparser)
[![PyPI](https://img.shields.io/pypi/v/geoparser.svg)](https://pypi.org/project/geoparser)
[![Downloads](https://static.pepy.tech/badge/geoparser)](https://pepy.tech/projects/geoparser)
[![Python](https://img.shields.io/pypi/pyversions/geoparser.svg)](https://pypi.org/project/geoparser)
[![License](https://img.shields.io/github/license/dguzh/geoparser.svg)](https://github.com/dguzh/geoparser/blob/main/LICENSE)

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

## Quick Start

```python
from geoparser import Geoparser
from geoparser.modules import SentenceTransformerResolver, SpacyRecognizer

# Build a pipeline from a recognizer and a resolver
gp = Geoparser(
    recognizer=SpacyRecognizer(),
    resolver=SentenceTransformerResolver(gazetteer_name="geonames"),
)

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

## Roadmap

Larger changes we intend to make — splitting the gazetteer and the default modules into standalone packages, and rethinking how documents and results are passed in and out — are described in [ROADMAP.md](ROADMAP.md).

## Contributing

Questions, bug reports, and ideas are always welcome via [issues](https://github.com/dguzh/geoparser/issues). Pull requests are appreciated too — see [CONTRIBUTING.md](CONTRIBUTING.md) for local setup and development guidelines.

## Acknowledgments

The Irchel Geoparser originated as part of my Master's thesis and was further developed with support from the [Department of Geography](https://www.geo.uzh.ch/) at the University of Zurich and the [Public Data Lab](https://publicdatalab.ch/) of the Digitalization Initiative of the Zurich Higher Education Institutions. I thank Prof. Dr. Ross Purves for the opportunity to continue this work as part of a research project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Third-party licenses are listed in [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).
