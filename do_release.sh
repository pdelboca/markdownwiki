#!/bin/bash
#
# Creates a new Github Release and uploads the artifacts.
#
# Positional parameters:
#  - BUMP: Supports the following common version components: major, minor, patch, stable, alpha, beta, rc, post, and dev.

set -e

BUMP=${1:-"patch"}
NEW_VERSION=$(uv version --bump $BUMP --short)
echo "Releasing new version: v$NEW_VERSION"

# Replace version number in main.py
sed -i "s/^\(__VERSION__ = *\)\"[^\"]*\"/\1\"$NEW_VERSION\"/" main.py
git add main.py
git add pyproject.toml
git add uv.lock

git commit -a -m "bump: Release v$NEW_VERSION"
git tag "v$NEW_VERSION"

# Create DEB file for Release.
./create-deb.sh

git push --tags
gh release create "v$VERSION" "dist/markdownwiki-linux-$NEW_VERSION.deb" --title "v$VERSION" --draft
