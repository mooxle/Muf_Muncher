#!/bin/sh
set -e
cd "$(dirname "$0")"

echo "[deploy-test] pulling latest from origin..."
git pull --ff-only origin main

echo "[deploy-test] building and (re)starting container..."
docker compose up -d --build

echo "[deploy-test] current status:"
docker compose ps
