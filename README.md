# tc_auth

`tc_auth` is an authentication module for FastAPI applications.

## Introduction

This repository provides reusable authentication components that can be attached to a FastAPI app backed by SQLAlchemy. It is focused on common identity workflows like registration, login, session lifecycle, and OAuth login.

## Basic Code Description

- `tc_auth/auth.py` contains the `Auth` class that wires core services and exception handling into your app.
- `tc_auth/service/` includes auth business logic such as signup/login, account operations, sessions, OTP handling, and OAuth integration.
- `tc_auth/db/models.py` defines SQLAlchemy models for accounts, OAuth accounts, sessions, and OTP records.
- `tc_auth/dependencies/` provides dependency helpers for current-user, role, and status checks.
- `tc_auth/jwt_handler.py` manages JWT token creation and validation used by authentication flows.

In short, this package acts as a compact authentication backend layer for API projects.
