#!/bin/bash

# clones and updates a dist-git repo

# shellcheck disable=SC2164

function die
{
	echo "Error: $1" >&2;
	exit 1;
}

function upload()
{
        [ -n "$RH_DIST_GIT_TEST" ] && return
        echo "# Bypassing lookaside upload to allow local development"
        # create a sources file with SHA512 checksum and filename
        for file in "$@"; do
            filename=$(basename "$file")
            checksum=$(sha512sum "$file" | awk '{print $1}')
            echo "$checksum  $filename" >> "$tmpdir/$SPECPACKAGE_NAME/sources"
            echo "Added to sources: $filename"
        done
}

if [ -z "$RHDISTGIT_BRANCH" ]; then
	echo "$0: RHDISTGIT_BRANCH is not set" >&2
	exit 1
fi

echo "Cloning the repository"
# clone the dist-git, considering cache
date=$(date +"%Y-%m-%d")
tmpdir="$(mktemp -d --tmpdir="$RHDISTGIT_TMP" RHEL"$RHEL_MAJOR"."$date".XXXXXXXX)"
cd "$tmpdir" || die "Unable to create temporary directory";
test -n "$RHDISTGIT_CACHE" && reference="-- --reference $RHDISTGIT_CACHE"
echo "Cloning using $RHPKG_BIN" >&2;
# shellcheck disable=SC2086
reference="$tmpdir/$SPECPACKAGE_NAME"
mkdir -p "$reference"
# RHGITURL provided as an argument to the make-dist command
# currently: https://gitlab.com/ndikshit/rocky-kernel-distgit; production URL to follow
git clone "$RHGITURL" "$reference" || die "Failed to clone $RHGITURL"

echo "Switching the branch"
# change in the correct branch
cd "$tmpdir/$SPECPACKAGE_NAME";
echo "/tmp folder: $SPECPACKAGE_NAME";
# RHDISTGIT_BRANCH provided as an argument to the make-dist command
# branch being used: rocky9
git checkout "$RHDISTGIT_BRANCH" 2>/dev/null || git checkout -b "$RHDISTGIT_BRANCH"
# Create the sources file (not directory)
echo "# Generated sources file for local development" > "$tmpdir/$SPECPACKAGE_NAME/sources"


echo "Unpacking from SRPM"
"$REDHAT"/scripts/expand_srpm.sh "$tmpdir"

# upload tarballs
# only modify sources file if it exists and is a regular file
if [ -f "$tmpdir/$SPECPACKAGE_NAME/{sources,.gitignore}" ]; then
    sed -i "/linux-.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME/sources" || true
    sed -i "/kernel-abi-stablelists.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME/sources" || true
    sed -i "/kernel-kabi-dw-.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME/sources" || true
fi
upload_list="$TARBALL $KABI_TARBALL $KABIDW_TARBALL"

echo "Uploading new tarballs: $upload_list"
# We depend on word splitting here:
# shellcheck disable=SC2086
upload $upload_list

echo "Creating diff for review ($tmpdir/diff) and changelog"
# diff the result (redhat/git/dontdiff). note: diff reuturns 1 if
# differences were found
diff -X "$REDHAT"/git/dontdiff -upr "$tmpdir/$SPECPACKAGE_NAME" "$REDHAT"/rpm/SOURCES/ > "$tmpdir"/diff;
# creating the changelog file

# changelog has been created by genspec.sh, including Resolves line, just copy it here
echo -e "${SPECPACKAGE_NAME}-${DISTBASEVERSION}\n" > "$tmpdir"/changelog
awk '1;/^Resolves: /{exit};' "$REDHAT"/"$SPECCHANGELOG" >> "$tmpdir"/changelog

# all done
echo "$tmpdir"
