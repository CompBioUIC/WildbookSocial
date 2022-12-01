import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="wildbook_social",
    version="0.0.1",
    author="",
    author_email="",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kirillovmr/wildbook-social",
    packages=setuptools.find_packages(),
    install_requires=[
        'pymongo==3.8.0',
        'ipython==7.7.0',
        'google-api-python-client==1.7.10',
    ],
    classifiers=[
        # How mature is this project? Common values are
        'DEVELOPMENT STATUS :: 3 - ALPHA',

        # Indicate who your project is intended for
        'Intended Audience :: Information Technology',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3",

        # Operating system
        "Operating System :: OS Independent",
    ],
)