# Release Notes Directory

This directory contains detailed release notes for each version of the ABB/FIMER PVI VSN REST integration.

## Structure

Each release has its own markdown file named with the version number:

- `v1.0.0-beta.1.md` - Beta 1 of version 1.0.0
- `v1.0.0.md` - Stable version 1.0.0
- `v1.1.0.md` - Future version 1.1.0
- etc.

## Viewing Release Notes

### For Users

- **Latest release notes:** Check the [CHANGELOG.md](../../CHANGELOG.md) in the root directory
- **Specific version details:** Browse files in this directory
- **GitHub releases:** Visit the [repository releases page](https://github.com/alexdelprete/ha-abb-fimer-pvi-vsn-rest/releases)

### For Developers

#### Release Philosophy

**⚠️ CRITICAL PRINCIPLES:**

1. **Published Releases are FROZEN**

   - Once a release is published (tagged and available on GitHub), its documentation is immutable
   - NEVER modify `docs/releases/vX.Y.Z.md` for a published version
   - NEVER change CHANGELOG.md entries for published versions
   - Published releases serve as historical record

1. **Version Progression**

   - After publishing vX.Y.Z, the master branch immediately becomes v(X.Y.Z+1)
   - All new work goes to the next version's documentation
   - Example: After publishing v1.0.0-beta.1 → immediately bump to v1.0.0-beta.2
   - All bug fixes, features, improvements documented in next version only

1. **Master Branch = Next Release**

   - The master branch always represents the NEXT release
   - Version in `manifest.json` and `const.py` reflects version being developed
   - All commits go toward the next release

**⚠️ Release Policy:**

**NEVER create git tags or GitHub releases automatically.** Only create them when explicitly instructed by the project maintainer. See [CLAUDE.md](../../CLAUDE.md) for complete
release policy and commit message guidelines.

#### Release Workflow

When creating a new release, follow these steps in order:

1. **Create detailed release notes**: Create `vX.Y.Z.md` or `vX.Y.Z-beta.N.md` using the template structure below
1. **Update CHANGELOG**: Update [CHANGELOG.md](../../CHANGELOG.md) with a summary section and links
1. **Bump manifest version**: Update version in [manifest.json](../../custom_components/abb_fimer_pvi_vsn_rest/manifest.json)
1. **Bump const version**: Update VERSION and STARTUP_MESSAGE in [const.py](../../custom_components/abb_fimer_pvi_vsn_rest/const.py)
1. **Commit changes**: `git add . && git commit -m "chore(release): bump version to vX.Y.Z"` (see [CLAUDE.md](../../CLAUDE.md) for commit format)
1. **Push commits**: `git push`
1. **⚠️ STOP - Get Approval**: Do NOT proceed without explicit maintainer instruction
1. **Create tag** (when instructed): `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push --tags`
1. **Create GitHub release** (when instructed): `gh release create vX.Y.Z --prerelease` (for beta) or `--latest` (for stable)

**After Publishing:**

Once the release is published on GitHub:

1. The release is now **FROZEN** - no changes to its documentation
1. Immediately bump version to next version (e.g., v1.0.0-beta.2 → v1.0.0-beta.3)
1. Create stub `docs/releases/v(next-version).md` for ongoing work
1. All subsequent changes documented in CHANGELOG.md under [Unreleased] or [next-version]
1. All new work goes to next version's release notes

## Release Note Template

Each release note file should include:

- Version number in title (with beta/stable indicator)
- Release date
- What's Changed summary
- Critical Bug Fixes (if any)
- New Features (if any)
- Code Quality Improvements
- Breaking Changes (if any)
- Dependencies
- Upgrade Notes
- Testing Recommendations
- Known Issues (if any)
- Acknowledgments (if applicable)
- Links to changelog, full diff, and documentation

## Navigation

- [← Back to CHANGELOG](../../CHANGELOG.md)
- [← Back to Repository Root](../../README.md)
