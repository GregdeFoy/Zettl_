# Updated setup.py
import os
import sys
from setuptools import setup, find_packages

# Determine platform-specific dependencies
if sys.platform == 'win32':
    platform_deps = ['pyreadline3', 'colorama']  # colorama for Windows color support
else:
    platform_deps = []

setup(
    name="zettl",
    version="0.7.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'python-dotenv',
        'requests',
        'rich',  # For enhanced terminal formatting
        'tqdm',  # For progress bars
        'anthropic',  # Claude API client
        'mcp',  # Model Context Protocol SDK
        'PyJWT',  # JWT token handling
    ] + platform_deps,
    entry_points='''
        [console_scripts]
        z=zettl.cli:cli
        zt=zettl.cli:cli
        zettl=zettl.cli:cli
    ''',
)