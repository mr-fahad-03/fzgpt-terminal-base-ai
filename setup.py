from setuptools import find_packages, setup

setup(
    name="fzgpt",
    version="0.1.0",
    description="Local AI CLI agent with Ollama, voice input, and safe action approvals",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "urllib3<2",
        "tomli>=2.0.0; python_version < '3.11'",
    ],
    extras_require={
        "voice": [
            "faster-whisper>=1.0.3",
            "numpy>=1.26.0",
            "sounddevice>=0.4.6",
        ],
        "dev": ["pytest>=8.2.0"],
    },
    entry_points={"console_scripts": ["fzgpt=fzgpt.cli:main"]},
)
