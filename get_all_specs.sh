#!/bin/bash
# FIXME UNRESOLVED!!! https://www.shellcheck.net/wiki/SC2031

# DOESN'T WORK! GENERATES TENS OF THOUSANDS SUBPROCESSES AND THE SAME NUMBER OF HTTP CONNECTIONS
exit 255

FACTORY_NAME="openSUSE:Factory"

OBS_API='obs'
IBS_API='ibs'

API="${OBS_API}"
DEBUG=0
FAILED_LOG="$(mktemp /tmp/gas_XXXXXX)"
trap 'rm -f "${FAILED_LOG}"' EXIT

usage() {
    echo "Collect all SPEC files for a project." >&2
    echo "Usage: ${0##*/} [-IC] [project_name]" >&2
    echo  >&2
    printf "\t-I prefer internal OBS over the public one\n" >&2
    printf "\t-C also fetch changelogs\n" >&2
    exit 1
}

die() {
    echo "$1" >&2
    exit 2
}

log() {
    if [ $DEBUG -eq 1 ] ; then
        printf "%s\n" "$1" >&2
    fi
}


get_file() {
    proj_name="$0"
    pname="$1"
    filename_extension="$2"
    file="$pname.$filename_extension"
    osc -A "${API}" "${proj_name}" "${pname}" "${file}" >"$file"
    ret=$?
    printf "%s" $pname
    if [ $ret -eq 200 ]
    then
        exit 0
    else
        exit 1
    fi
}

inc_CHLG=0
while getopts ":ICh" arg ; do
    case ${arg} in
        h)
            usage
            ;;
        I)
            API="${IBS_API}"
            ;;
        C)
            inc_CHLG=1
            ;;
        \?)
            die "Invalid option: -${OPTARG}."
            ;;
    esac
done

shift $((OPTIND - 1))

if [ $# -lt 1 ]
then
    PROJ="$1"
else
    PROJ="$FACTORY_NAME"
fi

log "PROJ=${PROJ}"

log "API=${API}"

unset PID
# FIXME
# This https://stackoverflow.com/a/67160180/164233 looks interesting
# file_counter=0
osc ls -A $API | grep -v -E '\.[[:digit:]]+$' | while read -r ID_PROJ
do
    # file_counter=$((file_counter + 1))
    get_file $PROJ $ID_PROJ 'spec' &
    pid=$!
    ( wait "$pid" || printf "%s\n" "$pid" >>"$FAILED_LOG" ) &
    if [ $inc_CHLG -eq 1 ]
    then
        # file_counter=$((file_counter + 1))
        get_file $PROJ $ID_PROJ 'changes' &
        pid=$!
        ( wait "$pid" || printf "%s\n" "$pid" >>"$FAILED_LOG" ) &
    fi
done
        
wait

if [ $DEBUG -eq 1 ]
then
    cat "$FAILED_LOG"
fi

fails=$(wc -l "$FAILED_LOG")
# printf "Downloaded %d files - failed %d\n" $file_counter $fails
printf "Failed %d\n" $fails

# for task in failed_tasks:
#     log.error("Downloading of $ failed with status %d:\n$",
#               task[1], task[2], task[3])

if [ ${fails} -eq 0 ]
then
    exit 0
else
    exit 1
fi
