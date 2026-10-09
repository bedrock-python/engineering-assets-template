#!/usr/bin/env bash
# Validates this hub before you push, the way its CI will see it:
#
#   1. `touchmark check` on a fresh copy of the working tree, committed as a
#      single commit, as "Use this template" creates a hub. Uncommitted and
#      untracked files count; ignored ones do not. While hub.yml still has the
#      template's placeholder id, check must fail with exactly that error, and
#      pass without warnings once an id and an owner are set in the copy. A
#      hub's CODEOWNERS must not name the template's @acme/hub-maintainers.
#   2. actionlint on the GitHub and the Gitea/Forgejo workflows. The GitLab CI
#      file needs a GitLab instance to lint (CI Lint in the project, or
#      `glab ci lint`), and bitbucket-pipelines.yml Bitbucket (its editor's
#      validator).
#   3. bitbucket-pipelines.yml and .azure-pipelines/touchmark.yml (the step
#      azure-pipelines.yml runs) run the touchmark image pinned by digest,
#      the same one as .gitlab-ci.yml.
#   4. With --release: no `TODO(release)` pin is left, so the workflows name
#      a real touchmark release (.azure-pipelines/touchmark.yml carries one
#      until a release runs a hub on Azure Pipelines).
#   5. With --public: no file git tracks or would add points readers of a
#      public repository at notes they cannot open: a design document by
#      number (RFC-NNNN) or section sign, a milestone name such as M2 or
#      M2.3, "the prototype", or text in Cyrillic, the language of those
#      notes. These are the rules of the template's own repository, whose
#      check in touchmark's CI passes --public; a hub with other rules
#      leaves it out.
#
# Usage: scripts/validate.sh [--release] [--public]
#
# Tools:
#   TOUCHMARK   the command that runs touchmark (default: touchmark), for
#               example "go run github.com/bedrock-python/touchmark/cmd/touchmark@v0.4.0"
#   ACTIONLINT  the command that runs actionlint (default: actionlint, else
#               its official image through docker)
#
# Exit status: 0 when everything passed, 1 when a check failed, 2 on a usage
# or setup error.
set -euo pipefail

actionlint_image="rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667"
placeholder_id="change-me"
placeholder_owner="@acme/hub-maintainers"

release=false
public=false
for arg in "$@"; do
  case "$arg" in
    --release) release=true ;;
    --public) public=true ;;
    -h | --help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) echo "validate: unknown argument $arg" >&2; exit 2 ;;
  esac
done

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$root"
failed=0
fail() { echo "FAIL: $*" >&2; failed=1; }
pass() { echo "ok: $*"; }

read -r -a touchmark <<<"${TOUCHMARK:-touchmark}"
if ! command -v "${touchmark[0]}" >/dev/null 2>&1; then
  echo "validate: ${touchmark[0]} not found; set TOUCHMARK to the command that runs touchmark" >&2
  exit 2
fi

# 1. touchmark check on a fresh single-commit copy.
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
hub="$work/hub"
mkdir "$hub"
while IFS= read -r -d '' path; do
  [ -f "$path" ] || continue # deleted from the working tree
  mkdir -p "$hub/$(dirname "$path")"
  cp -p "$path" "$hub/$path"
done < <(git ls-files -z --cached --others --exclude-standard)

commit() {
  git -C "$hub" -c core.autocrlf=false add -A
  git -C "$hub" -c user.name=validate -c user.email=validate@example.invalid \
    -c commit.gpgsign=false commit -q -m "$1"
}
check() {
  local out status=0
  out=$("${touchmark[@]}" check --hub "$hub" 2>&1) || status=$?
  printf '%s\n' "$out" | sed 's/^/  /'
  last_line=$(printf '%s\n' "$out" | tail -n 1 | tr -d '\r')
  check_output=$out
  return "$status"
}

git -C "$hub" -c init.defaultBranch=main init -q
commit "Initial commit"
if grep -qE "^id:[[:space:]]*\"?$placeholder_id\"?[[:space:]]*(#.*)?$" "$hub/hub.yml" 2>/dev/null; then
  echo "touchmark check: the template, with its placeholder id"
  status=0
  check || status=$?
  if [ "$status" -eq 2 ] && [ "$last_line" = "check failed: 1 error, 0 warnings" ] &&
    grep -q "still the template placeholder" <<<"$check_output"; then
    pass "check rejects the placeholder id, and only that"
  else
    fail "check of the template: want exactly the placeholder id error (exit 2), got exit $status: $last_line"
  fi
  sed -i.bak -E "s/^id:[[:space:]]*\"?$placeholder_id\"?/id: template-check/" "$hub/hub.yml"
  rm -f "$hub/hub.yml.bak"
  # Once the id is set, check warns about the placeholder owner of the
  # CODEOWNERS files: give the copy an owner, as README step 4 asks.
  for f in CODEOWNERS .github/CODEOWNERS .gitlab/CODEOWNERS .gitea/CODEOWNERS docs/CODEOWNERS; do
    if [ -f "$hub/$f" ]; then
      sed -i.bak "s#$placeholder_owner#@octo-org/hub-maintainers#g" "$hub/$f"
      rm -f "$hub/$f.bak"
    fi
  done
  commit "Set the hub id and its code owners"
  echo "touchmark check: the template, with an id"
  status=0
  check || status=$?
  if [ "$status" -eq 0 ] && [ "$last_line" = "ok" ]; then
    pass "check passes with an id, without warnings"
  else
    fail "check of the template with an id: want ok without warnings, got exit $status: $last_line"
  fi
else
  echo "touchmark check"
  status=0
  check || status=$?
  if [ "$status" -ne 0 ]; then
    fail "check: exit $status: $last_line"
  elif grep -q "names $placeholder_owner" <<<"$check_output"; then
    fail "a CODEOWNERS file still names $placeholder_owner: replace it with your team"
  else
    pass "check passes"
  fi
fi

# 2. actionlint on .github/workflows and .gitea/workflows.
workflows=()
for f in .github/workflows/*.yml .github/workflows/*.yaml .gitea/workflows/*.yml .gitea/workflows/*.yaml; do
  [ -f "$f" ] && workflows+=("$f")
done
if [ "${#workflows[@]}" -gt 0 ]; then
  echo "actionlint: ${workflows[*]}"
  # Gitea and Forgejo accept a full URL in uses:, which GitHub does not.
  ignore=(-ignore 'specifying action "https://[^"]*" in invalid format')
  status=0
  if [ -n "${ACTIONLINT:-}" ]; then
    read -r -a actionlint <<<"$ACTIONLINT"
    "${actionlint[@]}" "${ignore[@]}" "${workflows[@]}" || status=$?
  elif command -v actionlint >/dev/null 2>&1; then
    actionlint "${ignore[@]}" "${workflows[@]}" || status=$?
  elif command -v docker >/dev/null 2>&1; then
    mount=$root
    command -v cygpath >/dev/null 2>&1 && mount=$(cygpath -m "$root")
    MSYS_NO_PATHCONV=1 docker run --rm --name "touchmark-e2e-actionlint-$$" \
      -v "$mount:/repo:ro" -w /repo "$actionlint_image" \
      "${ignore[@]}" "${workflows[@]}" || status=$?
  else
    echo "validate: neither actionlint nor docker found; set ACTIONLINT" >&2
    exit 2
  fi
  if [ "$status" -eq 0 ]; then
    pass "actionlint"
  else
    fail "actionlint found problems (exit $status)"
  fi
fi

# 3. The images of bitbucket-pipelines.yml and .azure-pipelines/touchmark.yml:
# touchmark by digest, as on GitLab.
image_of() { sed -E 's/^[[:space:]]*(image|name):[[:space:]]*//; s/[[:space:]]+#.*$//; s/[[:space:]]*$//; s/^"(.*)"$/\1/'; }
if [ -f bitbucket-pipelines.yml ]; then
  # Without a match grep fails, and pipefail with set -e would end the
  # script silently: || true, and the empty result fails below.
  bb_image=$(grep -E '^image:' bitbucket-pipelines.yml | head -n 1 | image_of || true)
  gl_image=$(grep -E '^[[:space:]]+name:[[:space:]]*"?ghcr\.io/bedrock-python/touchmark' .gitlab-ci.yml 2>/dev/null | head -n 1 | image_of || true)
  if [ -z "$bb_image" ]; then
    fail "bitbucket-pipelines.yml has no top-level image: line; set image: to touchmark pinned by digest"
  elif ! grep -qE '^ghcr\.io/bedrock-python/touchmark:[^@[:space:]]+@sha256:[0-9a-f]{64}$' <<<"$bb_image"; then
    fail "bitbucket-pipelines.yml: the image is not touchmark pinned by digest: ${bb_image:-none}"
  elif [ -n "$gl_image" ] && [ "$bb_image" != "$gl_image" ]; then
    fail "bitbucket-pipelines.yml runs $bb_image, .gitlab-ci.yml $gl_image: pin one touchmark everywhere"
  else
    pass "bitbucket-pipelines.yml runs the pinned touchmark image"
  fi
fi
# The image of .azure-pipelines/touchmark.yml, which azure-pipelines.yml runs
# with docker: touchmark by digest, the one of .gitlab-ci.yml, named once.
azure_steps=.azure-pipelines/touchmark.yml
if [ -f azure-pipelines.yml ] || [ -f "$azure_steps" ]; then
  az_images=$(grep -oE 'ghcr\.io/bedrock-python/touchmark[^[:space:]]*' "$azure_steps" 2>/dev/null || true)
  gl_image=$(grep -E '^[[:space:]]+name:[[:space:]]*"?ghcr\.io/bedrock-python/touchmark' .gitlab-ci.yml 2>/dev/null | head -n 1 | image_of || true)
  if [ -z "$az_images" ]; then
    fail "$azure_steps names no touchmark image; it runs touchmark pinned by digest"
  elif [ "$(printf '%s\n' "$az_images" | wc -l)" -ne 1 ]; then
    fail "$azure_steps names the touchmark image more than once: keep one pin"
  elif ! grep -qE '^ghcr\.io/bedrock-python/touchmark:[^@[:space:]]+@sha256:[0-9a-f]{64}$' <<<"$az_images"; then
    fail "$azure_steps: the image is not touchmark pinned by digest: $az_images"
  elif [ -n "$gl_image" ] && [ "$az_images" != "$gl_image" ]; then
    fail "$azure_steps runs $az_images, .gitlab-ci.yml $gl_image: pin one touchmark everywhere"
  else
    pass "$azure_steps runs the pinned touchmark image"
  fi
fi

# 4. Placeholder pins of a touchmark release that did not exist yet.
pins=$(grep -rnE --exclude-dir=.git --exclude-dir=packs --exclude=validate.sh \
  "TODO\(release\)|touchmark@0{40}|touchmark:[^@[:space:]]*@sha256:0{64}" . || true)
if [ -n "$pins" ]; then
  if $release; then
    fail "placeholder pins of touchmark are left:"
  else
    echo "note: placeholder pins of touchmark (fails with --release):"
  fi
  printf '%s\n' "$pins" | sed 's/^/  /'
elif $release; then
  pass "touchmark is pinned to a release everywhere"
fi

# 5. References to notes a public reader cannot open, with --public. grep
# compares bytes (LC_ALL=C), so that GNU and BSD grep agree: in UTF-8 the
# section sign is C2 A7, and a Cyrillic letter is D0 to D3 followed by a
# continuation byte. A milestone or the word stands alone, as with \b.
if $public; then
  internal_refs="RFC-[0-9]{4}|"$'\xc2\xa7'"|(^|[^[:alnum:]_])(M[0-9](\.[0-9]+)?([^[:alnum:]_]|$)|[Pp]rototype)|"$'[\xd0-\xd3][\x80-\xbf]'
  refs=$(git ls-files -z --cached --others --exclude-standard -- . ':!scripts/validate.sh' |
    xargs -0 env LC_ALL=C grep -nIE -- "$internal_refs" 2>/dev/null || true)
  if [ -n "$refs" ]; then
    fail "files point at notes a public reader cannot open:"
    printf '%s\n' "$refs" | sed 's/^/  /'
  else
    pass "no references to notes a public reader cannot open"
  fi
fi

if [ "$failed" -ne 0 ]; then
  echo "validate: FAILED" >&2
  exit 1
fi
echo "validate: all checks passed"
