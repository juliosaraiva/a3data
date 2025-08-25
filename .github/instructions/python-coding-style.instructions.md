---
applyTo: "**/*.py"
---

This is a Python 3.13+ repository using modern Python development practices. Follow these guidelines when contributing to ensure maintainability, readability, and code quality.

## Environment & Tools

### Required Setup
- **Python Version**: Python 3.13+
- **Package Manager**: Use `uv` for all package and environment management
- **Linter/Formatter**: Use `ruff` for linting and formatting

### Required Before Each Commit
- Run `uv run ruff format .` to format code
- Run `uv run ruff check .` to lint code
- Fix all linting errors before committing

### Development Flow
- Install dependencies: `uv sync`
- Run tests: `uv run pytest`
- Type checking: `uv run pyright .`
- Full check: `uv run ruff check . && uv run ruff format --check . && uv run pytest && uv run pyright .`

## Code Standards

### Formatting & Style
- Follow PEP 8 with 88-character line limit
- Use double quotes for strings
- Prefer f-strings for string formatting
- Use trailing commas in multi-line structures
- Group imports: standard library, third-party, local
- Imports MUST be on the top of the file

### Type Hints
- Use type hints for all function parameters and return values
- Import types from `typing` or use built-in generics (Python 3.9+)
- BAD `variable: Optional[T]` / GOOD `variable: T | None`.
- BAD `variable: list` / GOOD `variable: list[str]`.

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes: prefix with single underscore `_`

### Documentation
- Use docstrings for all public functions, classes, and modules
- Follow Google or NumPy docstring format
- Include type information and examples for complex functions

### Error Handling
- Use specific exception types, avoid bare `except:`
- Prefer `raise ... from` for exception chaining
- Use context managers (`with` statements) for resource management

### Testing
- Write tests using `pytest`
- Use descriptive test function names: `test_function_should_behavior_when_condition`
- Organize tests in `tests/` directory mirroring source structure
- Aim for high test coverage of critical paths

## Key Guidelines
1. Write self-documenting code with clear variable and function names
2. Keep functions small and focused on single responsibilities
3. Use list/dict comprehensions when they improve readability
4. Prefer composition over inheritance
5. Use dataclasses or Pydantic models for structured data
6. Handle edge cases explicitly rather than relying on exceptions
7. Use logging instead of print statements for debugging
8. Follow the principle of least surprise in API design
