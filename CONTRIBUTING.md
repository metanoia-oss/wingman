# Contributing to Wingman

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment following the README
4. Create a branch for your changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_FORK/wingman.git
cd wingman

# Install in development mode
pip install -e .[dev]

# Build Node.js listener
cd node_listener
npm install
npm run build
cd ..

# Run setup wizard
wingman init
```

## Code Style

### Python
- Follow PEP 8 style guidelines
- Use type hints where practical
- Keep functions focused and small
- Add docstrings to public functions and classes

### TypeScript
- Use TypeScript strict mode
- Prefer `const` over `let`
- Use meaningful variable names

## Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, focused commits
   - Test your changes locally

3. **Test your changes**
   - Run the bot locally and verify it works
   - Test edge cases

4. **Submit a pull request**
   - Describe what your changes do
   - Reference any related issues

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Update documentation if needed
- Ensure the bot still works after your changes
- Be responsive to feedback

## Areas for Contribution

### Good First Issues
- Documentation improvements
- Adding more personality tones
- Improving error messages
- Adding unit tests

### Feature Ideas
- Support for additional LLM providers
- Web dashboard for configuration
- Message scheduling
- Multi-language support improvements

### Bug Reports
When reporting bugs, please include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (redact any personal information)

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow

## Questions?

Open an issue for questions or discussions about potential features.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
