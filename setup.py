from setuptools import setup, find_packages

# Explicitly list all packages for Windows compatibility
PACKAGES = [
    'lazypassword',
    'lazypassword.tui',
    'lazypassword.utils',
    'lazypassword.plugins',
    'lazypassword.plugins.builtins',
]

setup(
    name="lazypassword",
    version="1.0.0",
    packages=PACKAGES,
    install_requires=[
        "cryptography>=41.0.0",
        "pyperclip>=1.8.0",
        "textual>=0.47.0",
        "argon2-cffi>=23.1.0",
        "pyotp>=2.9.0",
        "paramiko>=3.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lazypassword=lazypassword.__main__:main",
        ],
    },
    python_requires=">=3.8",
    author="lazypassword",
    description="A terminal-based password manager inspired by LazyGit",
    keywords="password manager, tui, terminal, security",
)
