#!/bin/sh

SUBJ='Weekly report on packages in d:l:python*'
FROM="mcepl@cepl.eu"
REPORT_ADDR="opensuse-python@opensuse.org"
TESTED_REPOS="devel:languages:python:Factory devel:languages:python:certbot"
TESTED_REPOS="$TESTED_REPOS devel:languages:python devel:languages:python:azure"
TESTED_REPOS="$TESTED_REPOS devel:languages:python:avocado devel:languages:python:aws"
TESTED_REPOS="$TESTED_REPOS devel:languages:python:django devel:languages:python:flask"
TESTED_REPOS="$TESTED_REPOS devel:languages:python:jupyter devel:languages:python:numeric"
TESTED_REPOS="$TESTED_REPOS devel:languages:python:pyramid devel:languages:python:pytest"

function run() {
    for repo in "$@" ; do
        echo -e "\nNon-integrated packages in $repo:"
        ./find_non_integrated_packages.sh nonint "$repo"
        echo -e "\nPackages with diff in $repo:"
        ./find_non_integrated_packages.sh diff "$repo"
    done
}

cd /home/matej/archiv/2018/SUSE/projekty/pl3-scripts
git checkout -f master
git pull
(
    run $TESTED_REPOS
) | mail -s "$SUBJ" -r $FROM $REPORT_ADDR
