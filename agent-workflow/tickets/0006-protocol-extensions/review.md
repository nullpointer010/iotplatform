# Self-review

## Scope discipline
Touched only `app/schemas.py`, `app/routes/devices.py`, and one new test file.
No refactors of adjacent code, no doc churn beyond this ticket's folder.

## ACs vs. tests
| AC | Test(s) |
|----|---------|
| AC1 cross-protocol on POST | `test_post_http_with_mqtt_field_rejected`, `test_post_mqtt_with_plc_field_rejected`, `test_post_plc_with_lora_field_rejected` |
| AC2 required-fields on POST | `test_post_mqtt_missing_required_rejected` (+ existing 0003 tests) |
| AC3 field-format on POST | `test_post_mqtt_topic_invalid` (5 cases), `test_post_plc_bad_ip_rejected`, `test_post_lora_bad_eui_rejected`, `test_post_lora_bad_appkey_rejected`; happy paths `test_post_full_lora_succeeds`, `test_post_full_plc_succeeds` |
| AC4 PATCH protocol switch | `test_patch_switch_protocol_without_required_rejected`, `test_patch_switch_protocol_with_required_succeeds` |
| AC5 PATCH foreign-protocol field | `test_patch_introduces_foreign_protocol_field_rejected` |
| AC6 PATCH bad format | `test_patch_bad_format_rejected` |
| AC7 PATCH no-op / in-protocol | `test_patch_in_protocol_field_succeeds`, `test_patch_no_op_name_change_succeeds` |
| AC8 regression | 75/75 pytest green |

## Risks
- PATCH now rejects requests it previously accepted. This is a tightening, not
  a feature change; documented in journal.
- IPv4 only for `plcIpAddress`: deliberate, see journal.

## External review
