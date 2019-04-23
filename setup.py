import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

pkgs = setuptools.find_packages()
print('found these packages:', pkgs)

pkg_name = "hfoGUI"

setuptools.setup(
    name=pkg_name,
    version="1.0.5",
    author="Geoffrey Barrett",
    author_email="geoffrey.m.barrett@gmail.com",
    description="hfoGUI - a data visualization GUI for TINT data.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HussainiLab/hfoGUI.git",
    packages=pkgs,
    install_requires=
    [
        'PyQt5',
        'pillow',
        'numpy',
        'PyQtGraph',
        'scipy',
        'matplotlib',
        'pandas',
        'pyfftw'
    ],
    package_data={'hfoGUI': ['img/*.png']},
    classifiers=[
        "Programming Language :: Python :: 3.7 ",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3) ",
        "Operating System :: OS Independent",
    ],
)
