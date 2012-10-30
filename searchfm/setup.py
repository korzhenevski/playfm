from setuptools import setup, find_packages

setup(
    name='searchfm',
    version='1.0.0',
    author='Yura Nevsky',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'Flask==0.9',
        'gevent==0.13.7',
        'rvlib==0.9.2',
        'ngram==3.3.0',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'searchfm = searchfm.cli:main',
        ],
    },
)
