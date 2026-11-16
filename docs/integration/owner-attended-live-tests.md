# Owner-attended live integration runs

Live integration runs exercise the same judge-jev request cases used by the
controlled tests, with the request sent to the real Jev provider. The owner
must attend and manually trigger each run. Do not enable unattended live runs
in CI or in the unit-test suite.

## Before a run

1. Confirm the owner is present and has selected the platform and request cases
   to run.
2. Use the pinned judge-jev checkout and sc-agent client versions recorded in
   the run report. Confirm `.sc/judge-jev/settings.yaml` allows remote judging.
3. Supply credentials through sc-agent's normal lookup order: repository
   `.env`, `TYPESAFE_API_KEY`, then the default platform credential entry
   (`TYPESAFE_API_KEY`, current OS account). Do not pass keyring overrides.
4. Run the existing cases selected by the owner as real requests. Record the
   exact command, platform, runtime versions, commit and outcome. Do not
   substitute a fixture result for a live result.
5. Render one XHTML report from
   `templates/integration-report/report.xhtml.j2` for each platform actually
   tested. Include failures and partial runs. Commit the report with the code
   that produced the run and push it with the branch.

The template's consumer is the owner reviewing live compatibility before
phase completion. It gates the real-provider integration feature and captures
provider/runtime defects that controlled tests cannot reveal. Retire the guide
and template when judge-jev no longer supports owner-attended live integration
evidence.
