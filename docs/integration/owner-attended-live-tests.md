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
5. Render one XHTML panel from `templates/integration-report/report.xhtml.j2`
   for each platform actually tested. Include failures and partial runs. Use a
   JSON var file containing the template's required fields (`platform`,
   `run_utc`, `owner`, `judge_jev_commit`, `sc_agent_version`,
   `python_version`, `command_and_cases`, `outcome`, and
   `evidence_and_failures`), then render and publish it from the judge-jev
   checkout:

   ```sh
   PANEL="site/reports/integration/${PLATFORM}.xhtml"
   sc-compose render --root . \
     --file templates/integration-report/report.xhtml.j2 \
     --var-file "$REPORT_VARS" --strict --output "$PANEL"
   python "$SC_AGENT_CHECKOUT/templates/integration-report/render.py" \
     --panel "$PANEL" --reports-dir site/reports \
     --title "judge-jev live integration report: $PLATFORM"
   ```

   `SC_AGENT_CHECKOUT` must point to a sc-agent checkout containing the shared
   integration report generator (merged from `integrate/phase-b`). The shared
   generator copies the panel into a new run directory, renders the run's HTML
   page, and rebuilds `site/reports/index.html` newest first. Do not hand edit
   those generated files. Commit the panel, generated report tree, and the code
   that produced the run together, then push the branch.

The template's consumer is the owner reviewing live compatibility before
phase completion. It gates the real-provider integration feature and captures
provider/runtime defects that controlled tests cannot reveal. Retire the guide
and template when judge-jev no longer supports owner-attended live integration
evidence.
