#!/bin/bash

# Function to check if the current directory is a git repository
is_git_repo() {
    git rev-parse --is-inside-work-tree > /dev/null 2>&1
}

# Function to validate JSON files against a schema
validate_json() {
    schema=$1
    dir=$2
    for file in "$dir"/*.json; do
        if [ "$file" != "$schema" ]; then
            jq empty "$file" && check-jsonschema --schemafile "$schema" "$file"
            if [ $? -ne 0 ]; then
                echo "Validation failed for $file"
            else
                echo "Validated: $file"
            fi
        fi
    done
}

# Main script logic
if is_git_repo; then
    base_dir=$(git rev-parse --show-toplevel)
else
    read -p "Enter the base directory for JSON validation: " base_dir
fi

# Find directories containing 'schema.json' and validate JSON files in them
find "$base_dir" -type f -name 'schema.json' | while read schema; do
    dir=$(dirname "$schema")
    echo "Validating JSON files in $dir"
    validate_json "$schema" "$dir"
done
