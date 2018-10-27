from setuptools import setup
from setuptools import find_packages

setup(
    name='reactor-core',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        "appdirs==1.4.3",
        "attrs==18.2.0",
        "Babel==2.6.0",
        "black==18.9b0",
        "Click==7.0",
        "Delorean==1.0.0",
        "humanize==0.5.1",
        "loremipsum==1.0.5",
        "python-dateutil==2.7.5",
        "pytz==2018.6",
        "redis==2.10.6",
        "rq==0.12.0",
        "six==1.11.0",
        "toml==0.10.0",
        "tornado==5.1.1",
        "tzlocal==1.5.1"
    ]
)
