from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="sonar-reports",
    version="1.0.0",
    author="Esben Wiberg",
    author_email="",
    description="Generate customer-facing SAST reports from SonarCloud",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/esbenwiberg/sonar-reports",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "jinja2>=3.1.2",
        "click>=8.1.7",
        "tabulate>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "sonar-report=sonar_reports.cli:cli",
        ],
    },
    package_data={
        "sonar_reports": ["report/templates/*.j2"],
    },
    include_package_data=True,
)