# Description of the changes


Check all that apply:

- [ ] Updated documentation
- [ ] Source added/refactored
- [ ] Added unit tests
- [ ] Added widget/UI tests
- [ ] Updated packaging, dependency, or Pixi configuration

**References:**

- Links to IBM EWM items:
- Links to related issues or pull requests:

# Manual test for the reviewer

<!-- Include any manual validation steps, especially for NiceGUI widgets, ONCAT login/data-fetching behavior, or packaging changes. -->

# Checklist for the author

- [ ] `pixi run test` passes
- [ ] `pixi run build-docs` passes, if documentation changed
- [ ] `pixi run audit-deps` passes, if dependencies changed
- [ ] Documentation is updated or not required
- [ ] Versioning/package metadata changes were verified, if applicable

# Checklist for the reviewer

- [ ] Code follows project conventions and best software practices
- [ ] Variables and public names are clear
- [ ] Comments explain non-obvious intent, not mechanics
- [ ] Tests cover the changed behavior
- [ ] Documentation and packaging metadata are consistent with the change
