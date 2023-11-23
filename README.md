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
3. In the cloned GG2 directory, `poetry install`
