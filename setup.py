from setuptools import setup, find_packages

setup(
    name="shorts-splitter",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["ffmpeg-python"],
    entry_points={
        "console_scripts": [
            "shorts-splitter=cli:main",
        ],
    },
    author="JasonGu",
    author_email="guweizhai02@gmail.com",
    description="YouTube Shorts Auto-Splitter Tool",
    url="https://github.com/guweizhai02-claw/shorts-splitter",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
