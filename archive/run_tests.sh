#!/bin/bash
# This was a possible option to get around limitations with pytest
# It would also be language agnostic. It is somewhat feature limited compared
# to pytest, but mainly its just slower. I got around the limitiations
# and for now I'm back to pytest. This is the first bash I ever wrote tho,
# so I want to make sure its on the cloud for safe keeping.
red='\033[0;31m'
green='\033[0;32m'
clear='\033[0m' # No Color

set -x
old_fail_dit=`cat tests/fail.dit`
printf '%s' '' > /tmp/dit/test_output.txt
export NO_COLOR=1
json_files=$(find tests/json_data -name '*.json')
set -f
IFS=$'\n'
passed=0
failed=0
for json_file in $json_files; do
    while read -r test; do
        title=$(printf '%s\n' $test | jq -r '.title')
        printf '%s\n' $test | jq -r '.dit' > tests/fail.dit
        expected=$(printf '%s\n' $test | jq -r '.expected')
        dit tests/fail.dit > /tmp/dit/single_test.txt
        result=$(dit tests/fail.dit)

        if [ "$result" = "$expected" ]; then
            printf "${green}.${clear}"
            ((passed++))
        else
            #tput setaf 1
            printf "${red}F${clear}"
            printf "[%s] - '%s'  !=  '%s'\n\n" "$title" "${expected//$'\n'/$'\\n'}" "${result//$'\n'/$'\\n'}" >> /tmp/dit/test_output.txt
            ((failed++))
            exit 1
        fi
    done < <(jq -c '.dits[]' $json_file)
done
echo ''
printf "=== ${failed} failed, ${passed} passed ===\n" $failed $passed
$(/tmp/dit/test_output.txt)
echo ''
echo $old_fail_dit > tests/fail.dit
