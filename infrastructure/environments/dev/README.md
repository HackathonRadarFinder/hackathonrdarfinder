# DEV environment

## Purpose
Development validation for branch-based changes before integration to TEST and beyond.

## Defaults
- Namespace: `hackathon-dev`
- Replicas: 1
- Resource profile: reduced CPU and memory
- Database: isolated development database

## Verification
- Health endpoint responds successfully.
- Application connects to the database.
- CI validates backend/frontend on every PR or push to `develop`.
