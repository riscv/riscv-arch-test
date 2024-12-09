#!/bin/bash

# Check if requirements.txt exists
if [ ! -f requirements.txt ]; then
  echo "requirements.txt not found!"
  exit 1
fi

installed_count=0
not_installed_count=0

echo "Checking installed packages from requirements.txt..."

# Read each line in requirements.txt
while IFS= read -r requirement
do
  # Extract package name (ignoring version constraints)
  package=$(echo $requirement | sed 's/[><=].*//')

  # Check if the package is installed
  pip show $package > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "$package is not installed."
    not_installed_count=$((not_installed_count + 1))
    not_installed_packages="$not_installed_packages $package"
  else
    echo "$package is installed."
    installed_count=$((installed_count + 1))
  fi
done < requirements.txt

echo ""
echo "Total installed packages: $installed_count"
echo "Total not installed packages: $not_installed_count"

if [ $not_installed_count -gt 0 ]; then
  echo ""
  echo "To install missing packages, run:"
  echo "pip install$not_installed_packages"
fi

echo "Check complete."

