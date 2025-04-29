#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

NAME = "Rust Painter"
VERSION = "0.1"
DESCRIPTION = "Automatic Sign Art Painter for the game Rust by Facepunch"
AUTHOR = "Alexander Emanuelsson"
EMAIL = "Alexander.Emanuelsson94@gmail.com"
URL = "https://github.com/Johnnycyan/rust-painter"
REQUIRED = [
    "colorama==0.4.6",
    "MouseInfo==0.1.3",
    "numpy==2.2.5",
    "opencv-python==4.11.0.86",
    "pillow==11.2.1",
    "PyAutoGUI==0.9.54",
    "PyGetWindow==0.0.9",
    "PyMsgBox==1.0.9",
    "pynput==1.8.1",
    "pyperclip==1.9.0",
    "pypiwin32==223",
    "PyQt6==6.9.0",
    "PyQt6-Qt6==6.9.0",
    "PyQt6_sip==13.10.0",
    "PyRect==0.2.0",
    "PyScreeze==1.0.1",
    "pytweening==1.2.0",
    "pywin32==310",
    "six==1.17.0",
    "termcolor==3.0.1"
]

with open("README.md") as file:
    readme = file.read()

with open("LICENSE") as file:
    license = file.read()


setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=readme,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    license=license,
    install_requires=REQUIRED,
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)"
    ]
)
