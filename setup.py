"""setuptools packaging."""

import setuptools

setuptools.setup(
    name="dataworks_corporate_data_coalescence",
    version="0.0.1",
    author="DWP DataWorks",
    author_email="dataworks@digital.uc.dwp.gov.uk",
    description="Coalesces corporate memory files into larger objects",
    long_description="Lambdas that provision and query the metadata table",
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "query=coalescer:main"
        ]
    },
    package_dir={"": "coalescer"},
    packages=setuptools.find_packages("coalescer"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
