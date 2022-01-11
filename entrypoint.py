#/usr/bin/python3

import os, sys, subprocess
import github

testing = os.environ["INPUT_TESTING"] 
if testing:
  print("::info::Testing mode is on; will reset repositories!")

################################################################################
def rewind_repos():
  pass

################################################################################
def error_out(kind, msg):
  print(f"::error::{kind}::{msg}")
  if testing:
    rewind_repos()
  sys.exit(1)

################################################################################
def split_repo_and_dir(repo):
  """
  Split the input string
    org-name/repo-name/subdir-name/more/sub/dirs
  (where '/subdir-name/more/sub/dirs' is optional) into
    org-name/repo-name
  and
    subdir-name/more/sub/dirs
  The second part might be the empty string if no subdir-name was given.
  """
  parts = repo.split('/')
  if len(parts) == 2:
    return [repo, '']
  return ['/'.join(repo[0:2]), '/'.join(repo[2:])]

################################################################################
def get_gist_and_most_recent_sync_gistfile(github, gist_id):
  """
  Return the GistFile named `srsa-last-sync-sha.txt` in gist_id.
  error_out if the gist cannot be found.
  Return None if that file cannot be found in the gist.
  """
  gist = github.get_gist(gist_id)
  if not gist:
    error_out("config", f"Gist with id {gist_id} cannot be found!")
  try:
    return [gist, gist.files['srsa-last-sync-sha.txt']]
  except:
    return [gist, None]

################################################################################
def get_most_recent_sync_sha_and_date_in_gistfile(sha_file, tag):
  """
  Return the commit sha of the most recent successful sync, as stored in a
  GistFile `sha_file`. The line is expected to start with `tag`.
  Return None if that line cannot be found in the file.
  """
  try:
    sha_line = next(line for line in sha_file.content.splitlines if line.startswith(tag))
  except:
    return [None, None]
  sha_and_date = sha_line[len(tag):]
  return sha_and_date.split(' *DATE ')

################################################################################
def replace_most_recent_sync_sha_and_date_in_gistfile_content(sha_file, tag, sha):
  import datetime
  from email import utils
  nowdt = datetime.datetime.now()
  datestr = utils.format_datetime(nowdt)
  lines = []
  if sha_file:
    lines = sha_file.content.splitlines()
  updatedlines = []
  for line in lines:
    if not line.startswith(tag):
      updatedlines.append(line)
  updatedlines.insert(0, tag + sha + ' *DATE ' + datestr)
  return '\n'.join(updatedlines)

################################################################################
def set_most_recent_sync_sha_and_date_in_gistfile(gist, sha_file, tag, sha):
  """
  Store the commit sha of the most recent successful sync and now's daye in a
  GistFile `sha_file`. The line starts with `tag`.
  """
  editFiles = {}
  for filename in gist.files:
    if filename != 'srsa-last-sync-sha.txt':
      editFiles[filename] = github.InputFileContent(content=gist.files[filename].content)

  editContent = replace_most_recent_sync_sha_and_date_in_gistfile_content(sha_file, tag, sha)
  editFiles['srsa-last-sync-sha.txt'] = github.InputFileContent(content=editContent)

  from datetime import datetime
  gist.edit(description=f"Updated by sync-repo-subdir-action on {str(datetime.now())}", files=editFiles)


################################################################################
################################################################################
print("::group::Config sanity checks")

github_actor = os.environ["GITHUB_ACTOR"] 
github_token = os.environ["INPUT_GITHUB_TOKEN"]
g = github.Github(github_token)

source_repo, source_dir = split_repo_and_dir(os.environ["INPUT_SOURCE"])
target_repo, target_dir = split_repo_and_dir(os.environ["INPUT_TARGET"])

source_branch = os.environ["INPUT_SOURCE_BRANCH"]
target_branch = source_branch
if "INPUT_TARGET_BRANCH" in os.environ:
  target_branch = os.environ["INPUT_TARGET_BRANCH"]

print(f"::info::Source:: repo {source_repo} dir {source_dir if source_dir else '{NONE}'} branch {source_branch if source_branch else '{NONE}'}")
print(f"::info::Target:: repo {target_repo} dir {target_dir if target_dir else '{NONE}'} branch {target_branch if target_branch else '{NONE}'}")

# source = g.get_repo(source_repo)
#target = g.get_repo(target_repo)
#if not target.permissions.push:
#  error_out('config', f"Github token as provided to action does not have permission to push to {target_repo}")

gist, sha_file = get_gist_and_most_recent_sync_gistfile(g, os.environ["INPUT_GIST"])

print("::endgroup::")


################################################################################
print("::group::Determining previous sync commit")

tag = f"*SOURCE {os.environ['INPUT_SOURCE']} " \
  + f"*SOURCE_BRANCH {source_branch} " \
  + f"*TARGET {os.environ['INPUT_TARGET']}" \
  + f"*TARGET_BRANCH {target_branch} "
[prev_sha, prev_date] = get_most_recent_sync_sha_and_date_in_gistfile(sha_file, tag)

if prev_sha:
  print(f"::info::Last sync commit was {prev_sha}")
else:
  print(f"::info::Last sync commit not found, assuming first ever sync.")

print("::endgroup::")


################################################################################
print("::group::Checking out source repo")

try:
  os.mkdir("source")
except:
  subprocess.call(["ls", "-s", "source"])

subprocess.run(["git", "init"], cwd="source", check=True)
subprocess.run(["git", "remote", "set-url", "origin",  f"https://{github_actor}:{github_token}@github.com/{source_repo}"], cwd="source", check=True)
args = ["git", "fetch", "origin", source_branch]
if prev_date:
  args.insert(2, f"--shallow-since={prev_date}")
subprocess.run(args, cwd="source", check=True)
subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd="source", check=True)
with open('source/.git/info/sparse-checkout', 'w') as f:
    f.write(source_dir)
subprocess.run(["git", "pull", "origin", source_branch], cwd="source", check=True)

print("::info::source directory after checkout:")
subprocess.run(["ls"], cwd="source", check=True)

proc_res = subprocess.run(["git", "log", "-1", '--format="format:%H"', "HEAD"], \
  cwd="source", check=True, capture_output=True)
source_now_sha = proc_res.stdout.decode('utf-8').strip()
print(f"::info::newest source commit: {source_now_sha}")

print("::endgroup::")


################################################################################
print("::group::Getting source patch")

cmd = f"git format-patch --no-stat --find-renames --find-copies --stdout --keep-subject "
if prev_sha:
  cmd += f"{prev_sha}.. "
cmd += f"-- {source_dir} > ../patch"
subprocess.run(cmd, cwd="source", shell=True, check=True)

have_patch = True
if os.path.getsize('patch') < 10:
  print("::info::no patch to apply")
  have_patch = False
else:
  print("::info::patch to apply:\n")
  with open('patch', 'r') as patch:
    print(f.read())

print("::endgroup::")

################################################################################
print("::group::Checking out target repo")

if have_patch:
  os.mkdir("target")
  subprocess.run(["git", "init"], cwd="target", check=True)
  subprocess.run(["git", "remote", "set-url", "origin", \
    f"https://{github_actor}:{github_token}@github.com/{target_repo}"], cwd="target", check=True)
  subprocess.run(["git", "pull", "--depth=1", "origin", target_branch], cwd="target", check=True)

  print("::info::target directory after checkout:")
  subprocess.run(["ls"], cwd="target", check=True)
else:
  print("::info::skipped (no patch)")

print("::endgroup::")


################################################################################
print("::group::Applying patch to target")

if have_patch:
  dirignore = 1 # 1 for a/ vs b/
  if source_dir:
    dirignore += 1 # 1 more for having a "dir"
  dirignore += source_dir.count('/') # 1 extra for each *sub*dir
  args = ["git", "am", f"-p{dirignore}", "../patch"]
  if target_dir:
    args.append(f"--directory={target_dir}")
  subprocess.run(args, cwd="target", check=True)
else:
  print("::info::skipped (no patch)")

print("::endgroup::")


################################################################################
print("::group::Pushing to target")

if have_patch:
  subprocess.run(["git", "push", "origin", f"HEAD:{target_branch}"], cwd="target", check=True)
else:
  print("::info::skipped (no patch)")

print("::endgroup::")



################################################################################
print("::group::Update most recent successful sync commit")

set_most_recent_sync_sha_and_date_in_gistfile(gist, sha_file, tag, source_now_sha)

print("::endgroup::")
