#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "alias kand='cd $DIR; . venv/bin/activate; export FLASK_APP=qrave; export FLASK_ENV=development; code .;'" >>~/.bashrc
