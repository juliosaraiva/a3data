---
applyTo: "**/*"
---

# Git Conventions Guide

This guide establishes consistent git practices for commit messages, pull requests, and workflow to maintain clean project history and improve collaboration.

## 🚀 Commit Message Format

### Structure
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no functional change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system or dependency changes
- `ci`: CI/CD configuration changes
- `chore`: Other maintenance tasks

### Scope (Optional)
- `api`: API-related changes
- `auth`: Authentication/authorization
- `config`: Configuration changes
- `models`: Data models/schemas
- `services`: Service layer changes
- `utils`: Utility functions
- `tests`: Test-specific changes

### Examples
```bash
# Good examples
feat(api): add incident extraction endpoint
fix(auth): resolve token validation issue
docs(readme): update installation instructions
refactor(services): simplify error handling logic
test(api): add integration tests for health endpoint

# Bad examples (avoid these)
fix: bug fix
update stuff
WIP
asdf
```

## 📝 Commit Message Rules

### Do's ✅
- Use imperative mood ("add", not "added" or "adds")
- Keep subject line under 50 characters
- Capitalize first letter of subject
- Don't end subject with period
- Use body to explain "what" and "why", not "how"
- Separate subject and body with blank line
- Wrap body at 72 characters

### Don'ts ❌
- Don't use generic messages like "fix bug" or "update"
- Don't commit multiple unrelated changes together
- Don't use past tense ("fixed", "added")
- Don't include file names in subject (use scope instead)

## 🌿 Branch Naming

### Format
```
<type>/<short-description>
<type>/<issue-number>-<short-description>
```

### Types
- `feature/` or `feat/`: New features
- `fix/` or `bugfix/`: Bug fixes
- `hotfix/`: Critical fixes for production
- `docs/`: Documentation updates
- `refactor/`: Code refactoring
- `test/`: Test additions/updates
- `chore/`: Maintenance tasks

### Examples
```bash
# Good examples
feature/incident-extraction-api
fix/token-validation-error
docs/update-readme
refactor/simplify-error-handling
hotfix/critical-memory-leak

# With issue numbers
feat/123-add-user-authentication
fix/456-resolve-cors-issues
```

## 🔄 Pull Request Guidelines

### Title Format
```
<type>(<scope>): <description>
```
Same format as commit messages for consistency.

### Description Template
```markdown
## 📋 Summary
Brief description of changes and motivation.

## 🔧 Changes Made
- List of specific changes
- Another change
- Third change

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## 📚 Documentation
- [ ] README updated (if needed)
- [ ] API documentation updated
- [ ] Code comments added

## 🔗 Related Issues
Closes #123
Relates to #456
```

### Pull Request Rules

#### Before Creating PR
- [ ] Run `uv run ruff format .`
- [ ] Run `uv run ruff check . --fix`
- [ ] Run `uv run pyright .`
- [ ] Run `uv run pytest`
- [ ] Update documentation if needed
- [ ] Rebase on latest main branch

#### PR Requirements
- Clear, descriptive title
- Detailed description explaining changes
- Link to related issues
- Screenshots for UI changes
- Breaking changes clearly marked
- Tests passing in CI

## 🔀 Workflow Best Practices

### Development Flow
1. **Start from main**: Always branch from latest main
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/new-feature
   ```

2. **Make atomic commits**: Each commit should represent one logical change
   ```bash
   git add specific-files
   git commit -m "feat(api): add user authentication endpoint"
   ```

3. **Keep commits clean**: Use interactive rebase to clean up history
   ```bash
   git rebase -i HEAD~3  # Clean up last 3 commits
   ```

4. **Stay updated**: Regularly sync with main branch
   ```bash
   git fetch origin
   git rebase origin/main
   ```

### Before Merging
- [ ] Code review approved
- [ ] All checks passing
- [ ] No merge conflicts
- [ ] Documentation updated
- [ ] Tests passing

### Merge Strategy
- **Use "Squash and merge"** for feature branches
- **Use "Rebase and merge"** for hotfixes
- **Never use "Create a merge commit"** unless specifically needed

## 🚨 Emergency Procedures

### Hotfixes
```bash
git checkout main
git pull origin main
git checkout -b hotfix/critical-issue
# Make fixes
git commit -m "hotfix: resolve critical memory leak"
git push origin hotfix/critical-issue
# Create PR immediately
```

### Reverting Changes
```bash
# Revert specific commit
git revert <commit-hash>

# Revert merge commit
git revert -m 1 <merge-commit-hash>
```

## 📊 Git Aliases (Recommended)

Add these to your `~/.gitconfig`:
```ini
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = !gitk
    tree = log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit
    cleanup = !git branch --merged | grep -v '\\*\\|main\\|develop' | xargs -n 1 git branch -d
```

## 🔍 Quality Checks

### Pre-commit Checklist
- [ ] Code formatted with ruff
- [ ] No linting errors
- [ ] Type checking passes
- [ ] Tests pass locally
- [ ] Commit message follows conventions
- [ ] No sensitive data committed

### Code Review Focus
- Logic correctness
- Performance implications
- Security considerations
- Code maintainability
- Test coverage
- Documentation completeness

---

**Remember**: Good git practices make code history readable, debugging easier, and collaboration smoother. When in doubt, prefer clarity over brevity.
