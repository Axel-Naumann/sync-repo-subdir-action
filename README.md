# Sync Repo Subdir Action

Apply changes in a repository's subdir to another repository, syncing the latter to the former.
Instead of syncing overriding all history, this action builds a changeset (`format-patch`).
This changeset contains all patches between the previous sync to "now".
The commit hash of the most recent successful sync is stored in a gist.

## Inputs

### `source`

**Required** `org-name/repo-name/subdir-name`:

- `org-name/repo-name` is the GitHub repo of the commits to apply
- `subdir-name` is an optional subdirectory; only changes within this directory will be considered

### `source_branch`

**Required** Name of the source repo's branch, default branch (commonly `main` or `master`) if not given.

### `target`

**Required** `org-name/repo-name/subdir-name`:

- `org-name/repo-name` the GitHub repo of the commits to push to
- `subdir-name` is an optional subdirectory; all changes will be applied below this directory

### `target_branch`

**Optional** Name of the target repo's branch. Matches source branch if not given.

### `gist`

**Required** Gist ID as shown in gist URL, i.e. {id} in https://gist.github.com/{org}/{id}.
Must exist i.e. [create this first](https://gist.github.com/) with arbitrary content.

### `github_token`

**Required** Secret used to push to the target repo and to update the gist.

## Example usage

```yaml
uses: root-project/sync-repo-subdir-action@v1
with:
  source: "root-project/root/interpreter/cling"
  source_branch: "master"
  target: "root-project/cling"
  gist: "97321608e2aa04e2a6ecbc2b68a41a99"
  github_token: ${{ secrets.TOKEN }}
```
