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

Additionally, the code is checked for unused imports. Please make sure there are no such cases.

### Tests

This project uses `pytest` for unit testing. You can run the tests as follows:

```bash
poetry run pytest
```

This also creates a directory `htmlcov`, where you can check current test coverage. Simply open the `htmlcov/index.html` file in your browser. There you can see the test coverage per file and any statements that you may have missed in your tests.

Before submitting a pull request, make sure all tests pass and that they have been updated for any changes. When introducing new functionality, make sure to also add tests so that is covered from the beginning.

### Python Version

As of now, the project supports Python versions `>=3.11,<3.13` please keep your changes compatible. You can now use modern Python 3.11+ features like the union type syntax (`age: int | None = None`) instead of the typing library notation (`age: typing.Optional[int] = None`), though both are still acceptable.

## Licensing

See the [LICENSE](./LICENSE) file for the project's licensing.
