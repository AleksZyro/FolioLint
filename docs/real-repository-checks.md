# Real Repository Smoke Checks

FolioLint's automated tests stay offline. These commands are optional manual smoke checks for
the remote download path and should only be run when internet access is available.

## Public repositories

Run the commands from the FolioLint checkout:

```text
foliolint scan-url https://github.com/AleksZyro/FolioLint --explain
foliolint scan-url https://github.com/AleksZyro/PathLab --format markdown
foliolint scan-url https://github.com/AleksZyro/SortLab --format json
```

The exact scores can change as a repository changes. The useful smoke-check results are:

- the public URL is accepted;
- the default branch is downloaded, or a clear branch error is shown;
- the output contains checks and recommendations;
- the temporary workspace is removed after the command finishes.

To test a repository with another default branch, pass it explicitly:

```text
foliolint scan-url https://github.com/OWNER/REPO --branch develop --explain
```

These commands do not clone into the current folder and do not modify the scanned repository.
They download a temporary ZIP and remove it afterwards. Remote smoke checks are not part of CI,
because the normal test suite must remain deterministic and usable without internet access.
