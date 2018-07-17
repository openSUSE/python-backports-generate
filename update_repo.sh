#!/bin/bash

project="devel:languages:python:backports"

backports_python=($(osc ls $project))
factory_python=($(osc ls openSUSE:Factory |grep ^python))

python_itself=(
	"python-base"
	"python3-base"
	"python"
	"python3"
	"python-doc"
	"python3-doc"
)

# extra packages we want there
additional_links=(
	"libcryptopp"
	"libsodium"
	"qpid-proton"
	"openstack-macros"
)

factory_python=( "${factory_python[@]}" "${additional_links[@]}" )

# remove packages not in tumbleweed
for i in ${backports_python[@]}; do
	# skip packages in TW, or whitelisted
	if [[ "${factory_python[@]}" =~ "$i" ]]; then
		continue
	fi
	# delete all others
	osc rdelete $project $i -m "Package $i not in whitelist or openSUSE:Factory"
done

# add packages not in yet
for i in ${factory_python[@]}; do
	# skip actual python to not be backported
	if [[ "${python_itself[@]}" =~ "$i" ]]; then
		continue
	fi
	# already in the backports
	if [[ "${backports_python[@]}" =~ "$i" ]]; then
		continue
	fi
	osc linkpac openSUSE:Factory $i $project
done

