# Guiguts

Guiguts - an application to support creation of ebooks for PG
 
## Windows Development Setup

Minor alterations probably needed for other platforms

### Install Python

1. Download 3.10 from [python.org](https://www.python.org/).
2. Install – default dir is `C:\Users\<username>\AppData\Local\Programs\Python\Python310`
3. Ensure this dir is in PATH variable

### Install Poetry

1. https://python-poetry.org/docs/#installing-with-the-official-installer 
2. `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -`
3. Installs into `C:\Users\<username>\AppData\Roaming`
4. Adds top-level “poetry” wrapper in `C:\Users\<username>\AppData\Roaming\Python\Scripts`
5. Ensure the latter is in PATH variable

## macOS Development Setup

Developing Guiguts on macOS requires installing [Homebrew](https://brew.sh/) first.

### Install Python

Install python and python-tk using Homebrew. Note that we install and use a
specific version in the commands below for consistency with other developers.

```bash
brew install python@3.10 python-tk@3.10
```

### Install Poetry

We also install poetry using Homebrew.

```bash
brew install poetry
```

## Common Development Setup

1. Install Python & Poetry (above)
2. Clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
   or a fork thereof.
3. In the cloned GG2 directory, create a virtual environment using the version of
   python you installed above.
   * Windows (in git bash shell)
     ```bash
     poetry env use ~/AppData/Local/Programs/Python/Python310/python.exe
     ```
   * macOS
     ```bash
     poetry env use $(brew --prefix)/bin/python3.10
     ```
4. Also from the GG2 directory, install the GG2 python dependencies in the
   virtual environment. This will install GG2 as an editable package that you
   can develop and run directly.
   ```bash
   poetry install
   ```

You can run then GG2 directly with `poetry run guiguts`. For advanced users, 
you can access the virtual environment shell with `poetry shell`.

## Code style
Guiguts 2 uses [flake8](https://pypi.org/project/flake8) for static code analysis
and [black](https://pypi.org/project/black) for consistent styling. Both use
default settings, with the exception of maximum line length checking which is
adjusted in the recommended manner using the `.flake8` file to avoid conflicts
with black.

Both tools will be installed via `poetry` as described above.

`poetry run flake8 .` will check all `src` & `tests` python files.
`poetry run black .` will reformat all `src` & `tests` python files where necessary.

This project uses Github Actions to ensure neither of the above tools reports any
error.

Naming conventions from [PEP8](https://pep8.org/#prescriptive-naming-conventions)
are used. To summarize, class names use CapWords; constants are ALL_UPPERCASE;
most other variables, functions and methods are all_lowercase.

## Documentation
[Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
are used to document modules, classes, functions, etc.

`Sphinx` can be used to create HTML documentation by running the following command:
`poetry run python -m sphinx -b html docs docs/build`

HTML docs will appear in the `docs/build` directory.

This project uses Github Actions to ensure running `sphinx` does not report an error.

## Testing

`Pytest` is used for testing.

All tests can be run using the following command:
`poetry run pytest`

This project uses Github Actions to ensure running `pytest` does not report an error.

## Licensing

Copyright Contributors to the [Guiguts-py](https://github.com/DistributedProofreaders/guiguts-py) project

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

