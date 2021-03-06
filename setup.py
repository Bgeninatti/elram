import setuptools
from elram import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.build.txt", "r") as rf:
    requirements = list(rf.readlines())

setuptools.setup(
    name="elram",
    version=__version__,
    author="Bruno Geninatti",
    author_email="brunogeninatti@gmail.com",
    description="Un bot de telegram para ayudar con la gestión de la peña.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Bgeninatti/elram",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        'console_scripts': [
            'elram=elram.cli:main',
        ],
    },
)
