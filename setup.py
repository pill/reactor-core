from setuptools import setup
from setuptools import find_packages

setup(
    name='reactor-core',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'Delorean==0.4.5',
        'bleach==1.4.1',
        'futures==2.2.0',
        'ipdb',
        'mock==1.0.1',
        'nose==1.3.4',
        'pycurl',
        'pytz==2016.3',
        'requests==2.11.0',
        'rq-dashboard',
        'rq==0.5.6',
        'tornado==4.2',
        'python-dateutil==2.5.0',
        'loremipsum==1.0.5'
    ]
)
