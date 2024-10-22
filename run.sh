#!/bin/bash
set -e
gunicorn class_scheduler.wsgi --log-file -