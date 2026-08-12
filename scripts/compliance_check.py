#!/usr/bin/env python3
"""
compliance_check.py — Check content against brand compliance rules.
Scans for banned phrases, missing disclaimers, data claims, and platform-specific violations.

This is a safety gate, so it FAILS CLOSED:
- a severity word the gate doesn't recognize blocks (it does not downgrade to a warning);
- a rule the gate cannot evaluate (missing phrase, invalid regex) becomes a
  blocking rule_error instead of being skipped or crashing the run;
- a brand that doesn't exist at all is a FAILED lookup (likely a typo), never
  a silent SKIPPED pass.

Exit codes: 0 = PASSED / WARNING / SKIPPED (no rules configured),
            1 = BLOCKED, 2 = FAILED (unknown brand or unreadable rules file).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Persistent storage: prefer ${CLAUDE_PLUGIN_DATA} (survives sessions/updates),
# fall back to ~/socialforge-workspace (legacy/local)
_plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
if _plugin_data and Path(_plugin_data).exists():
    WORKSPACE = Path(_plugin_data) / "socialforge"
else:
    WORKSPACE = Path.home() / "socialforge-workspace"

# Severities that halt the pipeline. The schema authors rules as "block";
# older brand files use "critical". Both are hard stops. Any severity word
# NOT in either set is treated as blocking — an author who wrote "high" or
# "error" meant to stop the content, not to whisper.
BLOCKING_SEVERITIES = {"critical", "block"}
ADVISORY_SEVERITIES = {"warning", "warn", "advisory", "info", "notice"}


def _word_match(phrase, text):
    """Whole-word occurrence of `phrase` in `text` (both already case-folded
    by the caller). Substring matching is wrong for short phrases: 'ad' must
    not match 'advice'."""
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def normalize_disclaimers(disclaimers):
    """Normalize required_disclaimers to a list of (trigger, text, platforms).

    Accepts the schema form (list of {trigger, disclaimer, placement, platforms})
    and the legacy mapping form ({trigger: {disclaimer_text, platforms}}).
    """
    normalized = []
    if isinstance(disclaimers, dict):
        for trigger, config in disclaimers.items():
            if not isinstance(config, dict):
                config = {}
            text = config.get("disclaimer_text") or config.get("disclaimer") or ""
            normalized.append((str(trigger), text, config.get("platforms") or []))
    elif isinstance(disclaimers, list):
        for entry in disclaimers:
            if not isinstance(entry, dict):
                continue
            trigger = entry.get("trigger", "")
            if not trigger:
                continue
            text = entry.get("disclaimer") or entry.get("disclaimer_text") or ""
            normalized.append((str(trigger), text, entry.get("platforms") or []))
    return normalized


def normalize_image_rules(image_compliance):
    """Normalize image_compliance to a list of manual-review rule descriptions.

    Accepts the schema form (object of boolean/number sub-fields) and the
    legacy form (list of rule objects with check_method/rule/severity).
    """
    normalized = []
    if isinstance(image_compliance, list):
        for rule in image_compliance:
            if not isinstance(rule, dict):
                continue
            if rule.get("check_method") == "manual_flag":
                normalized.append((
                    rule.get("rule", "Image compliance check required"),
                    rule.get("severity", "warning"),
                ))
    elif isinstance(image_compliance, dict):
        labels = {
            "no_real_people": "Images must not depict identifiable real people",
            "no_competitor_logos": "Images must not contain competitor branding",
            "require_alt_text": "Images require alt text for accessibility",
        }
        for key, label in labels.items():
            if image_compliance.get(key):
                normalized.append((label, "warning"))
        min_diversity = image_compliance.get("min_diversity_score")
        if isinstance(min_diversity, (int, float)):
            normalized.append((
                f"Representation diversity across campaigns must score at least {min_diversity}",
                "warning",
            ))
        for subject in image_compliance.get("banned_imagery", []) or []:
            normalized.append((f"Images must never depict '{subject}'", "warning"))
    return normalized


def check_compliance(brand, text, platform=None):
    """Run compliance checks on text content. Returns the status string so
    main() can map it to an exit code."""
    brand_dir = WORKSPACE / "brands" / brand
    rules_path = brand_dir / "compliance-rules.json"

    if not brand_dir.exists():
        # An unknown brand is a probable typo, not a brand without rules —
        # reporting SKIPPED here would let a misspelled --brand pass the gate.
        brands_root = WORKSPACE / "brands"
        known = sorted(p.name for p in brands_root.iterdir() if p.is_dir()) if brands_root.exists() else []
        print(json.dumps({
            "status": "FAILED",
            "reason": f"Unknown brand '{brand}' — no such brand directory in the workspace",
            "known_brands": known,
            "violations": [], "warnings": [],
        }, indent=2))
        return "FAILED"

    if not rules_path.exists():
        print(json.dumps({"status": "SKIPPED",
                          "reason": "Brand exists but has no compliance-rules.json — no rules configured",
                          "violations": [], "warnings": []}))
        return "SKIPPED"

    try:
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({
            "status": "FAILED",
            "reason": f"compliance-rules.json is unreadable ({type(e).__name__}: {e}) — fix the file; the gate cannot pass content it cannot check",
            "violations": [], "warnings": [],
        }, indent=2))
        return "FAILED"

    violations = []   # Critical — blocks content
    warnings = []     # Advisory — flags but doesn't block
    rule_errors = []  # Rules the gate could not evaluate — these BLOCK (fail closed)

    # Check banned phrases
    for i, rule in enumerate(rules.get("banned_phrases", [])):
        if not isinstance(rule, dict) or not rule.get("phrase"):
            rule_errors.append({
                "type": "rule_error",
                "severity": "block",
                "rule_index": i,
                "reason": f"banned_phrases[{i}] has no 'phrase' — the gate cannot evaluate it",
                "suggestion": "Fix compliance-rules.json; an unevaluable rule is an unenforceable rule (fail closed)",
            })
            continue
        phrase = rule["phrase"]
        match_type = rule.get("match_type", "contains")
        case_sensitive = rule.get("case_sensitive", False)
        severity = rule.get("severity", "warning")

        found = False
        check_text = text if case_sensitive else text.lower()
        check_phrase = phrase if case_sensitive else phrase.lower()

        if match_type == "exact":
            # Whole-word phrase occurrence. (Comparing the phrase against the
            # entire caption made every "exact" rule dead code — no real
            # caption equals its banned phrase.)
            found = _word_match(check_phrase, check_text)
        elif match_type == "contains" and check_phrase in check_text:
            found = True
        elif match_type == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                if re.search(phrase, text, flags):
                    found = True
            except re.error as e:
                rule_errors.append({
                    "type": "rule_error",
                    "severity": "block",
                    "rule_index": i,
                    "phrase": phrase,
                    "reason": f"banned_phrases[{i}] regex does not compile: {e}",
                    "suggestion": "Fix the pattern in compliance-rules.json; a broken rule must not silently stop guarding (fail closed)",
                })
                continue

        if found:
            entry = {
                "type": "banned_phrase",
                "phrase": phrase,
                "severity": severity,
                "reason": rule.get("reason", ""),
                "suggestion": rule.get("suggestion", "")
            }
            sev = str(severity).lower()
            if sev in BLOCKING_SEVERITIES:
                violations.append(entry)
            elif sev in ADVISORY_SEVERITIES:
                warnings.append(entry)
            else:
                # Unknown severity word — fail closed. "high"/"error"/"blocker"
                # authors meant STOP; downgrading them to warnings ships the
                # exact content the rule existed to stop.
                entry["note"] = (f"severity '{severity}' is not a known level; "
                                 "treated as blocking (fail closed)")
                violations.append(entry)

    # Check data claims (statistics, percentages, dollar amounts)
    data_rules = rules.get("data_claim_rules", {})
    if data_rules.get("require_source", False):
        for pattern in data_rules.get("patterns_to_flag", [r"\d+%", r"\$[\d,]+"]):
            matches = re.findall(pattern, text)
            for match in matches:
                warnings.append({
                    "type": "data_claim",
                    "claim": match,
                    "severity": "warning",
                    "reason": "Data claim requires source verification",
                    "suggestion": f"Add source attribution for '{match}'"
                })

    # Check platform-specific rules
    if platform:
        platform_rules = rules.get("platform_specific_rules", {}).get(platform, {})

        # Hashtag limit
        max_hashtags = platform_rules.get("max_hashtags")
        if max_hashtags:
            hashtag_count = len(re.findall(r"#\w+", text))
            if hashtag_count > max_hashtags:
                warnings.append({
                    "type": "platform_rule",
                    "severity": "warning",
                    "reason": f"Too many hashtags: {hashtag_count} (max {max_hashtags} for {platform})",
                    "suggestion": f"Reduce to {max_hashtags} hashtags"
                })

        # Forbidden content types — whole-word matched: 'ad' must not hit
        # 'advice', and an empty entry must not match everything.
        forbidden = platform_rules.get("forbidden_content_types", [])
        if forbidden:
            for j, ftype in enumerate(forbidden):
                if not isinstance(ftype, str) or not ftype.strip():
                    rule_errors.append({
                        "type": "rule_error",
                        "severity": "block",
                        "reason": f"platform_specific_rules.{platform}.forbidden_content_types[{j}] is empty — an empty pattern would match ALL content",
                        "suggestion": "Remove the empty entry from compliance-rules.json",
                    })
                    continue
                if _word_match(ftype.strip().lower(), text.lower()):
                    violations.append({
                        "type": "forbidden_content",
                        "severity": "critical",
                        "reason": f"Content type '{ftype}' is forbidden on {platform}",
                        "suggestion": f"Remove or rephrase content related to '{ftype}'"
                    })

    # Check required disclaimers
    for trigger, disclaimer_text, trigger_platforms in normalize_disclaimers(rules.get("required_disclaimers", {})):
        # Check if trigger context applies
        if trigger.lower() in text.lower():
            # Disclaimer should be present
            if disclaimer_text and disclaimer_text.lower() not in text.lower():
                if not platform or platform in trigger_platforms or not trigger_platforms:
                    warnings.append({
                        "type": "missing_disclaimer",
                        "severity": "warning",
                        "trigger": trigger,
                        "reason": f"Content triggers '{trigger}' but required disclaimer is missing",
                        "suggestion": f"Add: {disclaimer_text}"
                    })

    # Check image compliance rules (text-based, not actual image analysis)
    for reason, severity in normalize_image_rules(rules.get("image_compliance", [])):
        # Flag for manual review
        warnings.append({
            "type": "image_compliance",
            "severity": severity,
            "reason": reason,
            "suggestion": "Manually verify this image rule before publishing"
        })

    # Rule errors block: a gate that cannot evaluate a rule cannot certify
    # the content that rule was written to stop.
    violations = rule_errors + violations
    status = "BLOCKED" if violations else ("WARNING" if warnings else "PASSED")
    print(json.dumps({
        "status": status,
        "critical_violations": len(violations),
        "warnings_count": len(warnings),
        "rule_errors": len(rule_errors),
        "violations": violations,
        "warnings": warnings
    }, indent=2))
    return status


def main():
    parser = argparse.ArgumentParser(description="SocialForge Compliance Checker")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--platform", default=None)
    args = parser.parse_args()

    status = check_compliance(args.brand, args.text, args.platform)
    # Exit codes so shell-level callers cannot sail past a blocked result:
    # 0 = PASSED/WARNING/SKIPPED, 1 = BLOCKED, 2 = FAILED (bad brand/rules file)
    if status == "BLOCKED":
        sys.exit(1)
    if status == "FAILED":
        sys.exit(2)


if __name__ == "__main__":
    main()
