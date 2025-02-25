#!/bin/bash

licenses_json="./licenses.json"
licenses="./THIRD_PARTY_LICENSES"


# Generate Licenses JSON
poetry run pip-licenses \
            --format=json \
            --with-license-file \
            --with-notice-file \
            --no-license-path > "$licenses_json"

# Create header
{
    echo "Third-Party Licenses"
    echo ""
    echo "This file contains license information for third-party dependencies used in this project."
    echo ""
    echo "================================================================================"
    echo ""
} > "$licenses"

# Loop over packages
jq -c '.[]' licenses.json | while read -r pkg; do
    NAME=$(echo "$pkg" | jq -r '.Name')
    VERSION=$(echo "$pkg" | jq -r '.Version')
    LICENSE=$(echo "$pkg" | jq -r '.License')
    LICENSE_TEXT=$(echo "$pkg" | jq -r '.LicenseText')
    NOTICE_TEXT=$(echo "$pkg" | jq -r '.NoticeText')

    {
        echo "Package: $NAME==$VERSION"
        echo "License: $LICENSE"
        echo ""
        echo "$LICENSE_TEXT"
        echo ""
    } >> "$licenses"


    if [ "$NOTICE_TEXT" != "UNKNOWN" ] && [ -n "$NOTICE_TEXT" ]; then
        {
        echo "NOTICE:" >> THIRD_PARTY_LICENSES
        echo "$NOTICE_TEXT" >> THIRD_PARTY_LICENSES
        echo ""
        } >> "$licenses"
    fi

    {
        echo "================================================================================"
        echo ""
    } >> "$licenses"
done

# Cleanup temporary files
rm -f licenses.json
