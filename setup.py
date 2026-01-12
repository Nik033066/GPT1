from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agentic-local",
    version="1.0.0",
    description="Local Multi-Agent AI System with Qwen",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.115.12",
        "uvicorn>=0.34.0",
        "aiofiles>=24.1.0",
        "pydantic>=2.10.6",
        "requests>=2.31.0",
        "numpy>=1.24.4",
        "colorama>=0.4.6",
        "python-dotenv>=1.0.0",
        "transformers>=4.46.3",
        "torch>=2.4.1",
        "ollama>=0.4.7",
        "selenium>=4.29.0",
        "markdownify>=1.1.0",
        "adaptive-classifier>=0.0.10",
        "langid>=1.1.6",
        "chromedriver-autoinstaller>=0.6.4",
        "httpx>=0.27,<0.29",
        "fake_useragent>=2.1.0",
        "selenium_stealth>=1.0.6",
        "undetected-chromedriver>=3.5.5",
        "openai",
        "accelerate",
    ],
    entry_points={
        "console_scripts": [
            "agentic=cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
