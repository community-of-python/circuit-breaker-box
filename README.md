# Python Circuit Breaker

A Python implementation of the Circuit Breaker pattern with Redis and in-memory storage support.

## Features

- 🚀 Implementations:
  - **Redis-based** - for distributed systems
  - **In-memory** - with TTLCache for local usage
- [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=FFD43B)](https://python.org) Python 3.10-3.13 support.
- ⚡ Asynchronous API
- 🔧 Configurable parameters
- 🛠️ FastAPI integration through custom exceptions
- 🔄 Exponential backoff by [tenacity](https://tenacity.readthedocs.io/en/latest/) with jitter for retries

## Usage
See -> `examples/example_circuit_breaker.py

### Commands
Use -> `Justfile`