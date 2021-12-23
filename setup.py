import os
import sys
import builtins
import versioneer

if sys.version_info[:2] < (3, 7):
    raise RuntimeError("Python version >= 3.7 required.")

builtins.__CALLSEQ_SETUP__ = True

if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

CONDA_BUILD = int(os.environ.get('CONDA_BUILD', '0'))
CONDA_ENV = os.environ.get('CONDA_PREFIX', '') != ''

from setuptools import setup, find_packages  # noqa: E402

DESCRIPTION = "CallSeq is a calling sequence recording tool"
LONG_DESCRIPTION = """\
CallSeq is a tool that allows recording the calling sequence of
functions or method calls during application runtime.

Currently, CallSeq can be applied to C++ based software.
"""


def setup_package():
    src_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    old_path = os.getcwd()
    os.chdir(src_path)
    sys.path.insert(0, src_path)

    if CONDA_BUILD or CONDA_ENV:
        # conda dependencies are specified in meta.yaml or conda
        # enviroment should provide the correct requirements - using
        # PyPI is unreliable, see below.
        install_requires = []
        setup_requires = []
        tests_require = []
    else:
        # Get requirements via PyPI. Use at your own risk as more than
        # once the numba and llvmlite have not matched.
        install_requires = open('requirements.txt', 'r').read().splitlines()
        setup_requires = ['pytest-runner']
        tests_require = ['pytest']

    scripts = [
        'callseq++=callseq.cli:main_cxx'
    ]

    metadata = dict(
        name='callseq',
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        license='BSD',
        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),
        author='Pearu Peterson',
        maintainer='Pearu Peterson',
        author_email='pearu.peterson@gmail.com',
        url='https://github.com/pearu/callseq',
        platforms='Cross Platform',
        classifiers=[
            "Intended Audience :: Developers",
            "License :: OSI Approved :: BSD License",
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            "Operating System :: OS Independent",
            "Topic :: Software Development",
        ],
        packages=find_packages(),
        package_data={'': ['*.hpp', '*.cpp']},
        entry_points={
            'console_scripts': scripts
        },
        install_requires=install_requires,
        setup_requires=setup_requires,
        tests_require=tests_require,
    )

    try:
        setup(**metadata)
    finally:
        del sys.path[0]
        os.chdir(old_path)
    return


if __name__ == '__main__':
    setup_package()
    del builtins.__CALLSEQ_SETUP__
