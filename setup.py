from setuptools import setup, find_packages

setup(
    name="lazypassword",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "pyperclip>=1.8.0",
        "textual>=0.47.0",
        "argon2-cffi>=23.1.0",
    ],
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
