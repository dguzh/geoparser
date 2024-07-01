# Developer Documentation

## Local development

This project uses [`poetry`](https://python-poetry.org/docs/) to manage dependencies. For installing poetry, visit the official [docs](https://python-poetry.org/docs/#installation).

For local development, you can install the package in virtual environment via `poetry`:

```bash
poetry install
poetry shell
```

We recommend you install the package in a virtual environment.

## Building

To build the package with `poetry`, use the `poetry build` command:

```bash
poetry build
```

This build the package in `sdist` and `wheel` format in the `dist` directory.

## Developer Guidelines

### Code formatting

`geoparser` code is formatted with `black` to ensure consistent formatting and to keep diffs as small as possible. Formatting is checked via a GitHub action on every push. Before submitting a pull request, please make sure that your code passes the formatting check.

These resources can provide a good start:

- [Official black documentation](https://black.readthedocs.io/en/stable/getting_started.html)
- [Formatting in VS Code](https://code.visualstudio.com/docs/python/formatting)

### Import order

Imports in `geoparser` are sorted with `isort` to ensure a consistent import order across all files. Import order is check via a GitHub action on every push. Before submitting a pull request, please make sure your code passes the import order check.

These resources can provide a good start:

- [Official isort documentation](https://pycqa.github.io/isort/index.html)

### Tests

This project uses `pytest` for unit testing. You can run the tests as follows:

```bash
poetry run pytest
```

Before submitting a pull request, make sure all tests pass or that they have been updated for any API changes. When introducing new functionality, make sure to also add tests so that is covered from the beginning.

## Licensing

See the [LICENSE](./LICENSE) file for the project's licensing.
