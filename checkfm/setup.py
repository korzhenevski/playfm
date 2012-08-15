from setuptools import setup, find_packages

setup(
    name="checkfm",
    version="0.9.0",
    author="Yura Nevsky",
    author_email="yura.nevsky@gmail.com",
    packages=find_packages(),
    install_requires=[
        'gevent==0.13.7',
        'pymongo==2.2.1',
        'redis==2.6.0',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'checkfm = checkfm.cli:main',
        ],
    },
)