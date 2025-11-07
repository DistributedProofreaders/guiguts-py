# Guiguts

Guiguts - an application to support creation of ebooks for PG

**If you want to use Guiguts primarily for developing the code, see below for [Developer Installation Notes](#developer-installation-notes).**

## User Installation Notes

This section contains notes from users who have installed Guiguts 2 on various platforms to use for PPing. **If you are a developer, you probably want the [Development Installation Notes](#common-development-setup).**

Note that although some example installation commands specify Python 3.11, Guiguts 2
also works with later versions of Python, and has been tested in versions up to 3.14.

### Windows

1. Install Python 3.11 or above from [Python.org](https://www.python.org/downloads/windows/).
GG has been tested in versions up to 3.14. Ensure the "Add Python to PATH" box is checked
during installation.
2. In a command window, type `pip3 install guiguts` (or `pip3 install guiguts --upgrade` to upgrade from a
previous version of GG2).
3. In a command window, Type `guiguts` to run GG2.

### macOS

1. Install Python 3.11 or above from [python.org](https://www.python.org/), not a Homebrew-installed Python.
GG has been tested in versions up to 3.14.

2. In a terminal window, type `pip3 install guiguts` (or `pip3 install guiguts --upgrade` to upgrade from a
previous version of GG2).

3. In a terminal window, type `guiguts` to run GG2.

4. If the above does not work, then try the following in a terminal window:

    a. Install pipx: `/usr/local/bin/python3 -m pip install pipx`

    b. Type `/usr/local/bin/python3 -m pipx install guiguts`
       (or `/usr/local/bin/python3 -m pipx install guiguts --upgrade`
       to upgrade from a previous version of GG2).

    c. Type `guiguts` or `~/.local/bin/guiguts` to run GG2.

### Linux (Debian/Ubuntu)

Python needs to be version 3.11 or above, and GG has been tested in
versions up to 3.14.

1. Install python, pipx, and Tk. Note that on some Linux distributions, the version number for `idle-python3.12` may differ slightly, e.g. as of this writing Debian 12 would require `idle-python3.11`.

    a. `apt-get update`

    b. `apt-get install -y python3 python3-pip python3-tk idle-python3.12 pipx`

2. Type `pipx install guiguts` (or `pipx upgrade guiguts` to upgrade from a previous version of GG2).

3. Add `$HOME/.local/bin` to your `$PATH` if it isn't already. Restart your shell / terminal window to refresh the path.

4. Type `guiguts` to run GG2.

### Linux (Fedora)

Instructions tested on Fedora Linux 42 (Workstation Edition). Note that Fedora Linux 43 is reported to include
Python 3.14 and Tk 9.0 rather than Tk 8.6. Guiguts does not yet support Tk 9.0, so at the moment is not
expected to run successfully on Fedora Linux 43. 

Fedora already has python3 installed. Note that python needs to be version 3.11 or above, and GG has been tested in
versions up to 3.13 (see note above regarding 3.14). Fedora does not include the awthemes package (see step 2 below)

1. Install pip, pipx, Tk & idle: `sudo dnf install pip pipx python3-tkinter python3-idle`

2. Install awthemes package:

    a. Download tcl-awthemes from https://sourceforge.net/projects/tcl-awthemes

    b. Extract awthemes-10.4.0 and from that directory: `sudo cp -r * /usr/share/tk8.6/`

3. Type `pipx install guiguts` (or `pipx upgrade guiguts` to upgrade from a previous version of GG2).

4. Type `pipx ensurepath` to ensure `guiguts` will be on your PATH.

5. Type `guiguts` to run GG2.

(Depending on your exact setup you may need to run `setxkbmap`, which will trigger Fedora to
offer to install the `setxkbmap` package.)

### Chromebook (after enabling Linux)

Check you have python3:

    python3 --version

If not:

    sudo apt install python3

Next, check you have pip:

    python3 -m pip --version

If not:

    sudo apt install python3-pip

Now try this command:

    python3 -m pip install guiguts

You might come across this error:

    error: externally-managed-environment

    × This environment is externally managed
    ╰─> To install Python packages system-wide, try apt install
        python3-xyz, where xyz is the package you are trying to
        install.
    
        If you wish to install a non-Debian-packaged Python package,
        create a virtual environment using python3 -m venv path/to/venv.
        Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
        sure you have python3-full installed.
    
        If you wish to install a non-Debian packaged Python application,
        it may be easiest to use pipx install xyz, which will manage a
        virtual environment for you. Make sure you have pipx installed.
    
        See /usr/share/doc/python3.11/README.venv for more information.

Let's go with the third option, and see if you have pipx: 

    pipx install guiguts

If you get this error:

    -bash: pipx: command not found

You need to install pipx:

    sudo apt install pipx

Then run this command before you install anything using pipx:

    pipx ensurepath

Open a new terminal or re-login and try this command:

    pipx install --include-deps guiguts

If you get an error saying no IdleLib module could be found:

    sudo apt-get install python3-Tk
    sudo apt-get install idle3

Now try the install command again:

    pipx install --include-deps guiguts

You'll need to use this command to open GG2 each time:

    pipx run guiguts

To update, you can use:

    pipx upgrade guiguts

#### Sources

https://stackoverflow.com/questions/6587507/how-to-install-pip-with-python-3
https://stackoverflow.com/questions/43987444/install-pip-for-python-3
https://realpython.com/python-pipx/
https://askubuntu.com/questions/1183317/modulenotfounderror-no-module-named-idlelib

## Developer Installation Notes

### Common Development Setup

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
3. You can then run GG2 directly with `poetry run guiguts`.

An alternative to `poetry run` is to enable your shell to use the poetry
environment. How to accomplish this differs depending which version of Poetry
you're using (which you can see by running `poetry --version`):

For Poetry 1, you can start a virtual environment shell with `poetry shell`,
then run GG2 with `guiguts`.

In Poetry 2, the `shell` command has been removed; instead, activate the virtual
environment with `eval $(poetry env activate)`. Once activated, you can run GG2
using `guiguts`.  To deactivate the environment and return to your base
environment, either exit the shell or run `deactivate`.

### Windows Development Setup

#### Install Python

##### Single (system-wide) version

1. Download Python 3.11 or above from [python.org](https://www.python.org/). GG has been
   tested in versions up to 3.14.
2. Install – default dir is `C:\Users\<username>\AppData\Local\Programs\Python\Python311`
3. Ensure this dir is in PATH variable

##### Using pyenv to install/use multiple Python versions

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

#### Install Poetry

1. https://python-poetry.org/docs/#installing-with-the-official-installer 
2. `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -`
3. Installs into `C:\Users\<username>\AppData\Roaming`
4. Adds top-level “poetry” wrapper in `C:\Users\<username>\AppData\Roaming\Python\Scripts`
5. Ensure the latter is in PATH variable

#### Clone the GG2 repo

Either clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
or a fork thereof.

#### Create virtual environment

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
     You may also need to tell poetry explicitly which python to use
     ```bash
     poetry env use 3.13.2
     ```

### macOS Development Setup

#### Install Python

Install python 3.11 or later from [python.org](https://www.python.org/). GG has been tested
in versions up to 3.14.

Note that installing python and python-tk using Homebrew is not supported for GG development.
Homebrew may install Tk version 9 instead of 8.6, which GG is optimized to use.

#### Install Poetry

1. Install pipx: `/usr/local/bin/python3 -m pip install pipx`
2. Install poetry: `/usr/local/bin/python3 -m pipx install poetry`

#### Clone the GG2 repo

Either clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
or a fork thereof.

#### Create virtual environment

In the cloned GG2 directory, create a virtual environment using a version of
python you installed above.

```bash
poetry env use /usr/local/bin/python3
```

### Linux Development Setup

1. Install Python, Poetry, etc.
   * Example from Ubuntu 22.04 -- adapt to your own Linux distro. Python should
     be version 3.11 or above, and GG has been tested in versions up to 3.14.
     ```bash
     sudo apt install python3.11 python3-pip python3-tk idle-python3.11 git pipx
     sudo pipx install poetry
     ## Test that Tk will work
     python3.11 -m tkinter
     ```
   * The last line above tests that Tk is working with Python. It should open a small
     window on your screen. Click the `Click me!` button to test mouse clicks, and
     `QUIT` to close the window, ending the test.
   * Potentially useful workaround for poetry install problems on CachyOS (Arch Linux):
     It may be necessary to run `poetry config keyring.enabled false`.
2. Clone the [GG2 Github repo](https://github.com/DistributedProofreaders/guiguts-py)
   or a fork thereof.
3. In the cloned GG2 directory, create a virtual environment using a version of
   python you installed above.
     ```bash
     poetry env use $(which python3.11)
     ```

### Code style

Guiguts 2 uses [flake8](https://pypi.org/project/flake8) and
[pylint](https://www.pylint.org) for static code analysis, and
[black](https://pypi.org/project/black) for consistent styling.  All use default
settings, with the exception of maximum line length checking which is adjusted
in the recommended manner (using the `.flake8` file and the `tool.pylint`
section of `pyproject.toml`) to avoid conflicts with black.

All of the above tools will be installed via `poetry` as described above.

`poetry run flake8 .` will check all `src` & `tests` python files.

`poetry run pylint --recursive y .` will check all `src` & `tests` python files.

`poetry run black .` will reformat all `src` & `tests` python files where necessary.

This project uses Github Actions to ensure none of the above tools report any
error.

Naming conventions from [PEP8](https://pep8.org/#prescriptive-naming-conventions)
are used. To summarize, class names use CapWords; constants are ALL_UPPERCASE;
most other variables, functions and methods are all_lowercase.

### Documentation

[Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
are used to document modules, classes, functions, etc.

[Sphinx](https://www.sphinx-doc.org/en/master/index.html) will be installed by
poetry (above) and can be used to create HTML documentation by running the following command:
```bash
poetry run python -m sphinx -q -b html docs docs/build
```

HTML docs will appear in the `docs/build` directory.

Sphinx can also be used to check coverage, i.e. that docstrings have been used everywhere
appropriate:
```bash
poetry run python -m sphinx -q -M coverage docs docs/build
```

This project uses Github Actions to ensure running sphinx does not report an error, and
that the coverage check does not report any undocumented items.

### Type checking

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

### Testing

[Pytest](https://docs.pytest.org) will be installed by poetry (above) and is used for testing.

All tests can be run using the following command:
`poetry run pytest`

Developers are encouraged to add tests (as appropriate) when new code is added to the project.

This project uses Github Actions to ensure running `pytest` does not report an error.

### Editor / IDE additional notes

#### Visual Studio Code

Several debugger configs are provided:

- "Guiguts"
    - Run Guiguts with debug output enabled
- "Guiguts (most recent file)"
    - Run Guiguts with debug output enabled
    - Open the most recently opened file
- "Guiguts (no debug output)"
    - Run Guiguts without debug output
- "Guiguts (use default settings)"
    - Run Guiguts with `--nohome` to not load your settings file
    - Therefore all settings should be reset to their defaults

Requirement: [Python Debugger][vsc_debugpy] extension

[vsc_debugpy]: https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy

Use the "Python: Select Interpreter" command to choose the appropriate Python environment. Your Poetry config should be detected and available to choose. If the Poetry config is not auto-detected, use `poetry env info -e` in the shell to find the Poetry-configured python interpreter. Then in the "Python: Select Interpreter" command, choose "Enter interpreter path..." and paste the full path to the `python` executable. 

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

