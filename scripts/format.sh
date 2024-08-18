#!/usr/bin/env bash
# This script formats all changed files from the last mergebase.
# You are encouraged to run this locally before pushing changes for review.

# Cause the script to exit if a single command fails
set -euo pipefail

FLAKE8_VERSION_REQUIRED="7.0.0"
BLACK_VERSION_REQUIRED="24.8.0"
SHELLCHECK_VERSION_REQUIRED="0.7.0"
MYPY_VERSION_REQUIRED="1.8.0"
ISORT_VERSION_REQUIRED="5.13.2"

check_python_command_exist() {
    VERSION=""
    case "$1" in
        black)
            VERSION=$BLACK_VERSION_REQUIRED
            ;;
        flake8)
            VERSION=$FLAKE8_VERSION_REQUIRED
            ;;
        mypy)
            VERSION=$MYPY_VERSION_REQUIRED
            ;;
        isort)
            VERSION=$ISORT_VERSION_REQUIRED
            ;;
        *)
            echo "$1 is not a required dependency"
            exit 1
    esac
    if ! [ -x "$(command -v "$1")" ]; then
        echo "$1 not installed. Install the python package with: pip install $1==$VERSION"
        exit 1
    fi
}

check_docstyle() {
    echo "Checking docstyle..."
    violations=$(git ls-files | grep '.py$' | xargs grep -E '^[ ]+[a-z_]+ ?\([a-zA-Z]+\): ' | grep -v 'str(' | grep -v noqa || true)
    if [[ -n "$violations" ]]; then
        echo
        echo "=== Found AgentStudio docstyle violations ==="
        echo "$violations"
        echo
        echo "Per the Google pydoc style, omit types from pydoc args as they are redundant."
        echo "If this is a false positive, you can add a '# noqa' comment to the line to ignore."
        exit 1
    fi
    return 0
}

check_python_command_exist black
check_python_command_exist flake8
# check_python_command_exist mypy
check_python_command_exist isort

# this stops git rev-parse from failing if we run this from the .git directory
builtin cd "$(dirname "${BASH_SOURCE:-$0}")"

ROOT="$(git rev-parse --show-toplevel)"
builtin cd "$ROOT" || exit 1

# NOTE(edoakes): black version differs based on installation method:
#   Option 1) 'black, 21.12b0 (compiled: no)'
#   Option 2) 'black, version 21.12b0'
#   For newer versions (at least 22.10.0), a second line is printed which must be dropped:
#
#     black, 22.10.0 (compiled: yes)
#     Python (CPython) 3.9.13
BLACK_VERSION_STR=$(black --version)
if [[ "$BLACK_VERSION_STR" == *"compiled"* ]]
then
    BLACK_VERSION=$(echo "$BLACK_VERSION_STR" | head -n 1 | awk '{print $2}')
else
    BLACK_VERSION=$(echo "$BLACK_VERSION_STR" | head -n 1 | awk '{print $3}')
fi
FLAKE8_VERSION=$(flake8 --version | head -n 1 | awk '{print $1}')
# MYPY_VERSION=$(mypy --version | awk '{print $2}')
ISORT_VERSION=$(isort --version | grep VERSION | awk '{print $2}')

# params: tool name, tool version, required version
tool_version_check() {
    if [ "$2" != "$3" ]; then
        echo "WARNING: AgentStudio uses $1 $3, You currently are using $2. This might generate different results."
    fi
}

tool_version_check "flake8" "$FLAKE8_VERSION" "$FLAKE8_VERSION_REQUIRED"
tool_version_check "black" "$BLACK_VERSION" "$BLACK_VERSION_REQUIRED"
# tool_version_check "mypy" "$MYPY_VERSION" "$MYPY_VERSION_REQUIRED"
tool_version_check "isort" "$ISORT_VERSION" "$ISORT_VERSION_REQUIRED"

if command -v shellcheck >/dev/null; then
    SHELLCHECK_VERSION=$(shellcheck --version | awk '/^version:/ {print $2}')
    tool_version_check "shellcheck" "$SHELLCHECK_VERSION" "$SHELLCHECK_VERSION_REQUIRED"
else
    echo "INFO: AgentStudio uses shellcheck for shell scripts, which is not installed. You may install shellcheck=$SHELLCHECK_VERSION_REQUIRED with your system package manager."
fi

if [[ $(flake8 --version) != *"flake8-quotes"* ]]; then
    echo "WARNING: AgentStudio uses flake8 with flake8_quotes. Might error without it. Install with: pip install flake8-quotes"
fi

if [[ $(flake8 --version) != *"flake8-bugbear"* ]]; then
    echo "WARNING: AgentStudio uses flake8 with flake8-bugbear. Might error without it. Install with: pip install flake8-bugbear"
fi

SHELLCHECK_FLAGS=(
  "--exclude=1090"  # "Can't follow non-constant source. Use a directive to specify location."
  "--exclude=1091"  # "Not following {file} due to some error"
  "--exclude=2207"  # "Prefer mapfile or read -a to split command output (or quote to avoid splitting)." -- these aren't compatible with macOS's old Bash
)

# TODO(dmitri): When more of the codebase is typed properly, the mypy flags
# should be set to do a more stringent check.
# MYPY_FLAGS=(
#     '--follow-imports=skip'
#     '--ignore-missing-imports'
# )

GIT_LS_EXCLUDES=(
  ':(exclude)docs/'
)

shellcheck_scripts() {
  shellcheck "${SHELLCHECK_FLAGS[@]}" "$@"
}

format_all() {
    command -v flake8 &> /dev/null;
    HAS_FLAKE8=$?

    # Run isort before black to fix imports and let black deal with file format.
    echo "$(date)" "isort...."
    git ls-files -- '*.py' "${GIT_LS_EXCLUDES[@]}" | xargs -P 10 \
      isort
    echo "$(date)" "Black...."
    git ls-files -- '*.py' "${GIT_LS_EXCLUDES[@]}" | xargs -P 10 \
      black
    # echo "$(date)" "MYPY...."
    # git ls-files -- '*.py' "${GIT_LS_EXCLUDES[@]}" | xargs -P 10 \
    #   mypy "${MYPY_FLAGS[@]}"
    if [ $HAS_FLAKE8 ]; then
      echo "$(date)" "Flake8...."
      git ls-files -- '*.py' "${GIT_LS_EXCLUDES[@]}" | xargs -P 5 \
        flake8 --config=.flake8
    fi

    if command -v shellcheck >/dev/null; then
      local shell_files bin_like_files
      shell_files=($(git ls-files -- '*.sh'))
      bin_like_files=($(git ls-files -- ':!:*.*' ':!:*/BUILD' ':!:*/Dockerfile' ':!:*README' ':!:*LICENSE' ':!:*WORKSPACE'))
      if [[ 0 -lt "${#bin_like_files[@]}" ]]; then
        shell_files+=($(git --no-pager grep -l -I -- '^#!\(/usr\)\?/bin/\(env \+\)\?\(ba\)\?sh' "${bin_like_files[@]}" || true))
      fi
      if [[ 0 -lt "${#shell_files[@]}" ]]; then
        echo "$(date)" "shellcheck scripts...."
        shellcheck_scripts "${shell_files[@]}"
      fi
    fi

    echo "$(date)" "done!"
}

# Format the entire directory.
format_all "${@:-}"
if [ -n "${FORMAT_SH_PRINT_DIFF-}" ]; then git --no-pager diff; fi

# check_docstyle

if ! git diff --quiet &>/dev/null; then
    echo 'Reformatted changed files. Please review and stage the changes.'
    echo 'Files updated:'
    echo

    git --no-pager diff --name-only

    exit 1
fi
