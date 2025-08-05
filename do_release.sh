#!/bin/bash
#
# Creates a push a new tag of the project. Release will be handled by Github Actions.
#
# Positional parameters:
#  - BUMP: Supports the following common version components: major, minor, patch, stable, alpha, beta, rc, post, and dev.

BUMP=${1:-"minor"}
NEW_VERSION=$(uv version --bump $BUMP --short)

# Replace version number in main.py
sed -i "s/^\(__VERSION__ = *\)\"[^\"]*\"/\1\"$NEW_VERSION\"/" main.py
git add main.py
git add pyproject.toml
git add uv.lock

git commit -a -m "bump: Release v$NEW_VERSION"
git tag "v$NEW_VERSION"
git push --tags

