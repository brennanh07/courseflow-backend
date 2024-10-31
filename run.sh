#!/bin/bash
set -e
gunicorn --timeout 120 --workers 3 --log-file - class_scheduler.wsgi:application