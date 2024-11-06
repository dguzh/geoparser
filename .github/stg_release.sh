# get latest version of pypi and testpypi from pip index
latest_version_pypi=$(pip index versions geoparser |& grep "geoparser" |& grep -Po "\d+\.\d+\.\d+[^)]*")
latest_version_testpypi=$(pip index versions geoparser --pre --index-url https://test.pypi.org/simple/ |& grep "geoparser" |& grep -Po "\d+\.\d+\.\d+[^)]*")
# parse the pyproject.toml file from the command line
package_version=$(cat pyproject.toml | grep "\[tool.poetry\]" -A 2 | tail -n 1 | grep -Po "\d+\.\d+\.\d+[^\"]*")

version_pattern="\d+\.\d+\.\d+"
testpypi_version=$(echo $latest_version_testpypi | grep -Po $version_pattern)
testpypi_suffix=$(echo $latest_version_testpypi | perl -pe "s/$version_pattern//g")
testpypi_suffix_number=$(echo $testpypi_suffix | grep -Po "\d+$")

>&2 echo "latest_version_pypi $latest_version_pypi"
>&2 echo "latest_version_testpypi $latest_version_testpypi"
>&2 echo "testpypi_version $testpypi_version"
>&2 echo "testpypi_suffix $testpypi_suffix"
>&2 echo "testpypi_suffix_number $testpypi_suffix_number"
>&2 echo "package_version $package_version"

# if the pypi version is the same as local, we are building a post-release
if [[ $latest_version_pypi == $package_version ]]; then
    >&2 echo "pypi version same as local, building post-release"

    # if the is a post-release for the same version already, we will increment from it
    if [[ "$testpypi_suffix" == *"post"* && "$testpypi_version" == "$package_version" ]]; then
        >&2 echo "existing post-release, incrementing..."
        new_suffix_number=$((testpypi_suffix_number+1))
        new_testpypi_release="${package_version}.post${new_suffix_number}"
    # in all other cases, we are building the post0 release
    else
        >&2 echo "no existing post-release, tagging with .post0..."
        new_testpypi_release="${package_version}.post0"
    fi

# if the local version is different (presumably higher), we are building an alpha version
else
    >&2 echo "pypi version differs from local, building an alpha version"

    # if the is an alpha for the same version already, we will increment from it
    if [[ "$testpypi_suffix" == *"a"* && "$testpypi_version" == "$package_version" ]]; then
        >&2 echo "existing alpha, incrementing..."
        new_suffix_number=$((testpypi_suffix_number+1))
        new_testpypi_release="${package_version}a${new_suffix_number}"
    # in all other cases, we are building the a0 release
    else
        >&2 echo "no existing alpha, tagging with a0..."
        new_testpypi_release="${package_version}a0"
    fi

fi
echo "$new_testpypi_release"
exit 0
