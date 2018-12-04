python-backports-generate
=========================
This repository is a collection of scripts to handle the
`devel:languages:python:backport`_ repository on the OpenBuildService.

backports_repo.py
-----------------
This script will sync the python packages between `openSUSE:Factory`_ and the `devel:languages:python:backport`_ project.
For Python packages available in `openSUSE:Factory`_, links will be created
from `openSUSE:Factory`_ to `devel:languages:python:backport`_ . If a package is
in `devel:languages:python:backport`_ but not in `openSUSE:Factory`_, the package
will be removed from `devel:languages:python:backport`_ .

There is the `backports_repo.json` configuration file which can handle additional
links needed. This is useful for extra BuildRequires (like `python-redis` BuildRequires
`redis` so `redis` needs to be in the `backports_repo.json` configuration file)

.. _`devel:languages:python:backport`: https://build.opensuse.org/project/show/devel:languages:python:backports
.. _`openSUSE:Factory`: https://build.opensuse.org/project/show/openSUSE:Factory
