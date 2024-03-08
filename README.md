# Guiguts

Guiguts - an application to support creation of ebooks for PG


## Common Development Setup

1. Install Python & Poetry, clone the repo and create a virtual environment,
   using the OS-specific instructions below.
2. After following the OS-specific instructions, in the cloned GG2 directory,
   install the GG2 python dependencies in the virtual environment. This will
   install GG2 as an editable package that you can develop and run directly.
   ```bash
   poetry install
   ```
   If additional dependencies are added to GG2, or you use pyenv to switch
   to a new version of python, you will need to re-run this command.
3. You can then run GG2 directly with `poetry run guiguts`. Alternatively, 
   you can start a virtual environment shell with `poetry shell`, then run
   GG2 with `guiguts`.
 
 
## Windows Development Setup

### Install Python

#### Single (system-wide) version

1. Download Python 3.11 from [python.org](https://www.python.org/).
2. Install – default dir is `C:\Users\<username>\AppData\Local\Programs\Python\Python311`
3. Ensure this dir is in PATH variable

#### Using pyenv to install/use multiple Python versions

[pyenv](https://github.com/pyenv/pyenv/blob/master/README.md) lets you easily switch between
multiple versions of Python, if that would be useful for development/testing.

1. Clone the pyenv-win repo: `git clone https://github.com/pyenv-win/pyenv-win.git "$HOME\.pyenv"`
2. Add environment variables (can execute these in a Powershell window):
    ```powershell
    [System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
    [System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
    [System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
    [System.Environment]::SetEnvironmentVariable('path', $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")
    ```
3. In a new shell, install version(s) of Python, e.g. `pyenv install 3.11.7`,
`pyenv install 3.12.0`, etc.
4. To set python version, use `pyenv global 3.11.7`, for example.

### Install Poetry

1. https://python-poetry.org/docs/#installing-with-the-official-installer 
2. `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -`
3. Installs into `C:\Users\<username>\AppData\Roaming`
4. Adds top-level “poetry” wrapper in `C:\Users\<username>\AppData\Roaming\Python\Scripts`
5. Ensure the latter is in PATH variable

### Clone the GG2 repo

Either clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
or a fork thereof.

### Create virtual environment

In the cloned GG2 directory, create a virtual environment using a version of
python you installed above.
   * Single python version (in git bash shell)
     ```bash
     poetry env use ~/AppData/Local/Programs/Python/Python311/python.exe
     ```
   * If using pyenv (in git bash shell)
     ```bash
     poetry config virtualenvs.prefer-active-python true
     ```


## macOS Development Setup

Developing Guiguts on macOS requires installing [Homebrew](https://brew.sh/) first.

### Install Python

Install python and python-tk using Homebrew. Note that we install and use a
specific version in the commands below for consistency with other developers.

```bash
brew install python@3.11 python-tk@3.11
```

### Install Poetry

We also install poetry using Homebrew.

```bash
brew install poetry
```

### Clone the GG2 repo

Either clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
or a fork thereof.

### Create virtual environment

In the cloned GG2 directory, create a virtual environment using a version of
python you installed above.

```bash
poetry env use $(brew --prefix)/bin/python3.11
```


## Linux Development Setup

1. Install Python, Poetry, etc.
   * Example from Ubuntu 22.04 -- adapt to your own Linux distro
     ```bash
     sudo apt install python3.11 python3-pip python3-tk idle-python3.11 git
     sudo python3.11 -m pip install poetry
     ## Test that Tk will work
     python3.11 -m tkinter
     ```
   * The last line above tests that Tk is working with Python. It should open a small
     window on your screen. Click the `Click me!` button to test mouse clicks, and
     `QUIT` to close the window, ending the test.
2. Clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
   or a fork thereof.
3. In the cloned GG2 directory, create a virtual environment using a version of
   python you installed above.
     ```bash
     poetry env use $(which python3.11)
     ```


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

[Sphinx](https://www.sphinx-doc.org/en/master/index.html) will be installed by
poetry (above) and can be used to create HTML documentation by running the following command:
```bash
poetry run python -m sphinx -b html docs docs/build`
```

HTML docs will appear in the `docs/build` directory.

Sphinx can also be used to check coverage, i.e. that docstrings have been used everywhere
appropriate:
```bash
poetry run python -m sphinx -M coverage docs docs/build`
```

This project uses Github Actions to ensure running sphinx does not report an error, and
that the coverage check does not report any undocumented items.


## Type checking

[Mypy](https://mypy.readthedocs.io/en/stable/index.html) will be installed by
poetry (above) and is used for static type checking. Where developers have added 
[type hints](https://peps.python.org/pep-0484/), mypy will issue warnings when those
types are used incorrectly.

It is not intended that every variable should have its type annotated, but developers
are encouraged to add type hints to function definitions, e.g.
```python
def myfunc(num: int) -> str:
    ...
```
Note that functions without type annotation will not be type checked. The
[type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
has a summary of how to use type annotations for various common situations.

To type check the Guiguts package and the test routines:
```bash
poetry run mypy -p guiguts
poetry run mypy tests
```

## Testing

[Pytest](https://docs.pytest.org) will be installed by poetry (above) and is used for testing.

All tests can be run using the following command:
`poetry run pytest`

Developers are encouraged to add tests (as appropriate) when new code is added to the project.

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

