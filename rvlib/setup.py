from setuptools import setup, find_packages
from proto_cmd import build_proto, clean_proto

setup(
    name="rvlib",
    version="0.9.0",
    author="Yura Nevsky",
    author_email="yura.nevsky@gmail.com",
    packages=find_packages(),
    install_requires=['protobuf==2.4.1',],
    zip_safe=False,
    cmdclass = { 'build_proto': build_proto,
                 'clean': clean_proto }
)