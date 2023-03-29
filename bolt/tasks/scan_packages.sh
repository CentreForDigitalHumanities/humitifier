#!/bin/bash

# This entire script is generated by ChatGPT :)

if [[ -n "$(command -v apt)" ]]; then

    # get manually installed packages
    packages=$(apt-mark showmanual)

    # initialize json array
    json='{"packages":['

    # loop through each package
    for package in $packages; do
        # get package name and version
        name=$(dpkg -s $package | awk '/^Package: /{print $2}')
        version=$(dpkg -s $package | awk '/^Version: /{print $2}')
        # add package to json array
        json+='{"name":"'$name'", "version":"'$version'"},'
    done

    # remove trailing comma and close json array
    json=${json%?}
    json+=']}'

    echo $json


elif [[ -n "$(command -v rpm)" ]]; then

    # Get a list of manually installed packages
    rpm -qa --qf '%{NAME}\n' > /tmp/packages.txt

    # Loop through each package and extract the name and version
    printf '{\n'
    printf '\t"packages": [\n'
    while read package; do
        version=$(rpm -q "${package}" --qf '%{VERSION}')
        printf "\t\t{\"name\": \"%s\", \"version\": \"%s\"}," "${package}" "${version}"
    done < /tmp/packages.txt | sed '$s/,$//' # Remove the comma at the end of the last package entry
    printf '\n\t]\n}'
    rm /tmp/packages.txt

else

    echo "Neither 'apt' nor 'rpm' package managers are available on this system."
    exit 1

fi