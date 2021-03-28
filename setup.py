import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="Webservice Sandbox",
    version="0.0.1",
    author="Ryan Marchildon",
    description=("A playground for practices architecture best practices."),
    license="BSD",
    packages=['webservice', 'tests'],
    long_description=read('README.md'),
    setup_requires=["black"],
    install_requires=read("requirements.txt") 
)