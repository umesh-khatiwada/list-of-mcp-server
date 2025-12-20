# Pre-commit Hooks Setup for CAI-JOBS Project

This project now has pre-commit hooks configured to maintain code quality and consistency.

## What's Configured

- **Black**: Python code formatting with 88-character line length
- **isort**: Import statement sorting and organization
- **flake8**: Python linting with permissive rules for existing code
- **autoflake**: Automatic removal of unused imports and variables
- **General hooks**: Trailing whitespace, end-of-file fixing, merge conflict detection

## Files Created

1. `.pre-commit-config.yaml` - Main pre-commit configuration
2. `.pre-commit-config-full.yaml` - Full configuration with YAML/Dockerfile linting (backup)
3. `.flake8` - Flake8 configuration
4. `.yamllint.yml` - YAML linting configuration
5. `pyproject.toml` - Black and isort configuration
6. `run-precommit.sh` - Script to run pre-commit on this project only

## Usage

### Manual Check
Run pre-commit on your files before committing:
```bash
./run-precommit.sh
```

### Automatic on Commit
Pre-commit hooks are installed and will run automatically when you commit:
```bash
git add .
git commit -m "Your commit message"
```

### Run on All Files
To run all hooks on all files in the project:
```bash
pre-commit run --all-files --config .pre-commit-config.yaml
```

### Skip Hooks (if needed)
To commit without running hooks:
```bash
git commit -m "Your message" --no-verify
```

## Configuration Details

### Black (Code Formatting)
- Line length: 88 characters
- Python 3.9+ target
- Automatically formats Python code

### isort (Import Sorting)
- Black-compatible profile
- Sorts and organizes imports

### Flake8 (Linting)
- Ignores: E203 (whitespace before ':'), E722 (bare except), W503 (line break before operator)
- Line length: 88 characters
- Focuses on important code quality issues

### File Scope
All hooks are configured to only run on files within the `7.02-CAI-JOBS/` directory, so they won't interfere with other projects in the repository.

## Troubleshooting

### Pre-commit Not Running
```bash
# Reinstall hooks
pre-commit install

# Check hook status
pre-commit --version
```

### Formatting Issues
```bash
# Run black manually
black main.py

# Run isort manually
isort main.py
```

### Update Hooks
```bash
# Update to latest versions
pre-commit autoupdate
```

## Customization

To modify the configuration:
1. Edit `.pre-commit-config.yaml` for hook settings
2. Edit `.flake8` for linting rules
3. Edit `pyproject.toml` for Black/isort settings

The setup is designed to be non-intrusive and focused on maintaining good code quality without being overly strict on the existing codebase.
