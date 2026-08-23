from glob import glob

from setuptools import find_packages, setup

nome = "rover_frugal_control"

setup(
    name=nome,
    version="2.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{nome}"]),
        (f"share/{nome}", ["package.xml"]),
        (f"share/{nome}/config", glob("config/*.yaml")),
        (f"share/{nome}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Eduardo Matheus Figueira",
    maintainer_email="eduardomatheusfigueira@gmail.com",
    description="Cinemática 4WS, molas passivas e supervisor do Rover Frugal.",
    license="TODO: definir",
    entry_points={
        "console_scripts": [
            f"cinematica_4ws = {nome}.no_cinematica:main",
            f"molas_passivas = {nome}.no_molas_passivas:main",
            f"tracao = {nome}.no_tracao:main",
            f"supervisor = {nome}.no_supervisor:main",
        ],
    },
)
