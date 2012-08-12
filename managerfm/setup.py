from setuptools import setup, find_packages

setup(
    name="managerfm",
    version="0.9.0",
    author="Yura Nevsky",
    author_email="yura.nevsky@gmail.com",
    packages=find_packages(),
    install_requires=[
        'gevent==0.13.7',
        'gevent-zeromq==0.2.5',
        'pymongo==2.2.1',
        'redis==2.6.0',
	'rvlib==0.9.2',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'managerfm = managerfm.cli:main',
        ],
    },
)
