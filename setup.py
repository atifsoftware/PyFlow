from setuptools import setup, find_packages

setup(
    name="shohaghinfo-pyflow",
    version="3.0.8",
    author="shohaghinfo",
    author_email="shohaghinfo@gmail.com",
    description="A lightweight MVC framework for Python with fluent query builder, routing and active record ORM.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/atifsoftware/PyFlow",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "pyflow-init=core.cli_init:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pymysql>=1.1.1",
        "psycopg2-binary>=2.9.10",
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        "a2wsgi>=1.10.0",
        "gunicorn>=23.0.0",
        "Pillow>=12.3.0",
        "email-validator>=2.0.0",
    ],
)
