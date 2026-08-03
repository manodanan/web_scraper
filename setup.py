from setuptools import setup

setup(
    name="backend-finder",
    version="1.0.0",
    description="Machine Learning Powered Application Backend & API Finder CLI",
    author="Web Auditing Tools",
    py_modules=["backend_finder", "ml_backend_classifier"],
    install_requires=[
        "requests",
        "beautifulsoup4",
        "playwright",
        "scikit-learn",
        "numpy",
        "joblib"
    ],
    entry_points={
        "console_scripts": [
            "backend-finder=backend_finder:main",
            "backend_finder=backend_finder:main",
        ],
    },
    data_files=[
        ("share/man/man1", ["backend_finder.1"]),
    ],
)
