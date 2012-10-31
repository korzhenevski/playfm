from setuptools import setup, find_packages

setup(
    name='cometfm',
    version='1.0.0',
    author='Yura Nevsky',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[
        'Flask==0.9',
        'gevent==0.13.7',
	    'gevent-zeromq==0.2.5',
        'redis==2.6.0',
        'rvlib==0.9.2',
        'hiredis==0.1.1',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'cometfm = cometfm.cli:main',
        ],
    },
)
