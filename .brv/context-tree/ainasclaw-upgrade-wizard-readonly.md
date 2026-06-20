# AiNasClaw upgrade wizard readonly rule

- On UPGRADE, the wizard must not allow changing the workspace directory or gateway port.
- `src/wizard_templates/upgrade_uifile` marks both fields `disabled: true` and shows a note.
- `src/service-setup.sh` hard-preserves existing workspace and port during upgrade, ignoring wizard-submitted values.
- Validate with `bash -n src/service-setup.sh`.
