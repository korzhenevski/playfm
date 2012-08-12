from setuptools import setup, find_packages

setup(
    name="rvlib",
    version="0.9.2",
    author="Yura Nevsky",
    author_email="yura.nevsky@gmail.com",
    packages=find_packages(),
    install_requires=['protobuf==2.4.1',],
    zip_safe=False
)
