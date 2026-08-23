from glob import glob

from setuptools import find_packages, setup

nome = "rover_frugal_bringup"

setup(
    name=nome,
    version="2.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{nome}"]),
        (f"share/{nome}", ["package.xml"]),
        (f"share/{nome}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Eduardo Matheus Figueira",
    maintainer_email="eduardomatheusfigueira@gmail.com",
    description="Integração e ensaios do Rover Frugal em simulação.",
    license="TODO: definir",
    entry_points={
        "console_scripts": [
            f"registrador = {nome}.registrador:main",
            f"piloto_ensaio = {nome}.piloto_ensaio:main",
        ],
    },
)
