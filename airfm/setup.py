from setuptools import setup, find_packages

setup(
    name='airfm',
    version='0.1.0',
    author='outself',
    author_email='team@again.fm',
    packages=find_packages(),
    install_requires=[],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'airfm = airfm:main',
        ],
    },
)
