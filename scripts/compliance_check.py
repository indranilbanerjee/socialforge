#!/usr/bin/env python3
"""
compliance_check.py — Check content against brand compliance rules.
Scans for banned phrases, missing disclaimers, data claims, and platform-specific violations.
"""

import argparse
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path.home() / "socialforge-workspace"


def check_compliance(brand, text, platform=None):
    """Run compliance checks on text content."""
    rules_path = WORKSPACE / "brands" / brand / "compliance-rules.json"

    if not rules_path.exists():
        print(json.dumps({"status": "SKIPPED", "reason": "No compliance rules configured", "violations": [], "warnings": []}))
        return

    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    violations = []  # Critical — blocks content
    warnings = []    # Advisory — flags but doesn't block

    # Check banned phrases
    for rule in rules.get("banned_phrases", []):
        phrase = rule["phrase"]
        match_type = rule.get("match_type", "contains")
        case_sensitive = rule.get("case_sensitive", False)
        severity = rule.get("severity", "warning")

        found = False
        check_text = text if case_sensitive else text.lower()
        check_phrase = phrase if case_sensitive else phrase.lower()

        if match_type == "exact" and check_phrase == check_text:
            found = True
        elif match_type == "contains" and check_phrase in check_text:
            found = True
        elif match_type == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            if re.search(phrase, text, flags):
                found = True

        if found:
            entry = {
                "type": "banned_phrase",
                "phrase": phrase,
                "severity": severity,
                "reason": rule.get("reason", ""),
                "suggestion": rule.get("suggestion", "")
            }
            if severity == "critical":
                violations.append(entry)
            else:
                warnings.append(entry)

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

        # Forbidden content types
        forbidden = platform_rules.get("forbidden_content_types", [])
        if forbidden:
            # Check if any forbidden type keywords appear in the text
            for ftype in forbidden:
                if ftype.lower() in text.lower():
                    violations.append({
                        "type": "forbidden_content",
                        "severity": "critical",
                        "reason": f"Content type '{ftype}' is forbidden on {platform}",
                        "suggestion": f"Remove or rephrase content related to '{ftype}'"
                    })

    # Check required disclaimers
    disclaimers = rules.get("required_disclaimers", {})
    for trigger, config in disclaimers.items():
        disclaimer_text = config.get("disclaimer_text", "")
        trigger_platforms = config.get("platforms", [])

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
    for rule in rules.get("image_compliance", []):
        if rule.get("check_method") == "manual_flag":
            # Flag for manual review
            warnings.append({
                "type": "image_compliance",
                "severity": rule.get("severity", "warning"),
                "reason": rule.get("rule", "Image compliance check required"),
                "suggestion": "Manually verify this image rule before publishing"
            })

    status = "BLOCKED" if violations else ("WARNING" if warnings else "PASSED")
    print(json.dumps({
        "status": status,
        "critical_violations": len(violations),
        "warnings_count": len(warnings),
        "violations": violations,
        "warnings": warnings
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="SocialForge Compliance Checker")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--platform", default=None)
    args = parser.parse_args()

    check_compliance(args.brand, args.text, args.platform)


if __name__ == "__main__":
    main()
