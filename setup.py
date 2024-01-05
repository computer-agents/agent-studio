from setuptools import setup, find_packages

# Reading requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='desktop_env',
    version='0.1.0',
    packages=find_packages(),
    install_requires=requirements,
    author='Your Name',
    author_email='your.email@example.com',
    description='A brief description of the desktop_env module',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/desktop_env',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
    entry_points={
        'console_scripts': [
            'desktop_env=desktop_env.__main__:main'
        ],
    },
)
