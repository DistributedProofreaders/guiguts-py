# Guiguts-2.0-tkinter

Guiguts rewrite using Python/tkinter
 
 
## Windows-focused dev installation

Minor alterations probably needed for other platforms

## Install Python

    1. Download 3.10 from python.org
    2. Install – default dir is `C:\Users\<username>\AppData\Local\Programs\Python\Python310`
    3. Ensure this dir is in PATH variable

## Install Poetry

1. https://python-poetry.org/docs/#installing-with-the-official-installer 
2. `(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -`
3. Installs into `C:\Users\<username>\AppData\Roaming`
4. Adds top-level “poetry” wrapper in `C:\Users\<username>\AppData\Roaming\Python\Scripts`
5. Ensure the latter is in PATH variable

## Set up Development System

1. Install Python & Poetry (above)
2. Clone the [GG2 Github repo](https://github.com/windymilla/Guiguts-2.0-tkinter)
3. In the cloned GG2 directory, `poetry install`. The message
   ".../guiguts does not contain any element" can be ignored (or suppressed by using
   `poetry install --no-root` instead).

## Code style
Guiguts 2 uses [flake8](https://pypi.org/project/flake8) for static code analysis
and [black](https://pypi.org/project/black) for consistent styling. Both use
default settings, with the exception of maximum line length checking which is
adjusted in the recommended manner using the `.flake8` file to avoid conflicts
with black.

Both tools will be installed via `poetry` as described above.

`poetry run flake8 src` will check all `src` python files.
`poetry run black src` will reformat all `src` python files where necessary.

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
