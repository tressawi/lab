"""Golden dataset evaluation for prompt quality assessment."""

import os
import json
import re
import pandas as pd
from typing import Optional

from app_config import GOLDEN_DATASET_FILE, MODEL_NAME, BASE_DIR
from optimization_logger import OptimizationLogger


class PromptEvaluator:
    """Evaluates prompts against golden dataset with detailed logging."""

    def __init__(self, client, logger: OptimizationLogger):
        """
        Initialize evaluator.

        Args:
            client: Google GenAI client
            logger: OptimizationLogger for console/file logging
        """
        self.client = client
        self.logger = logger
        self.model_name = MODEL_NAME

    def load_golden_dataset(self) -> pd.DataFrame:
        """Load golden dataset from CSV file."""
        if not os.path.exists(GOLDEN_DATASET_FILE):
            self.logger.log("EVAL:LOAD", "No golden dataset found",
                           detail=f"Expected file at: {GOLDEN_DATASET_FILE}")
            return pd.DataFrame()

        df = pd.read_csv(GOLDEN_DATASET_FILE)
        self.logger.log("EVAL:LOAD", f"Loaded {len(df)} test cases from golden dataset",
                       detail=df.to_string())
        return df

    def _run_prompt_on_contract(self, prompt: str, contract_text: str) -> dict:
        """Run a prompt against a contract and return parsed result."""
        formatted_prompt = prompt.format(contract_text=contract_text)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=formatted_prompt
        )

        response_text = response.text

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response_text)
        if json_match:
            response_text = json_match.group(1).strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            result = {
                "recommendation": "ERROR",
                "reasoning": f"Failed to parse: {response_text[:200]}",
                "key_findings": [],
                "suggested_changes": []
            }

        return result

    def _check_assertions(self, assertions: str, actual_findings: list) -> tuple:
        """
        Check if assertions are satisfied by actual findings.

        Returns:
            Tuple of (passed: bool, details: str)
        """
        if assertions.lower() == "none" or not assertions:
            return True, "No assertions to check"

        keywords = [kw.strip().lower() for kw in assertions.split(";")]
        findings_text = " ".join(str(f).lower() for f in actual_findings)

        passed = []
        failed = []
        for kw in keywords:
            if kw in findings_text:
                passed.append(kw)
            else:
                failed.append(kw)

        all_passed = len(failed) == 0
        details = f"Passed: {passed}, Failed: {failed}"
        return all_passed, details

    def _calculate_coverage(self, expected_findings: str, actual_findings: list) -> float:
        """Calculate coverage score based on expected vs actual findings."""
        if not expected_findings:
            return 1.0

        expected_keywords = [kw.strip().lower() for kw in expected_findings.split(";")]
        findings_text = " ".join(str(f).lower() for f in actual_findings)

        matched = sum(1 for kw in expected_keywords if kw in findings_text)
        return matched / len(expected_keywords) if expected_keywords else 1.0

    def _check_format_compliance(self, result: dict) -> tuple:
        """
        Check if result has valid format.

        Returns:
            Tuple of (valid: bool, errors: list)
        """
        errors = []
        required_fields = ["recommendation", "reasoning", "key_findings"]

        for field in required_fields:
            if field not in result:
                errors.append(f"Missing field: {field}")

        if "recommendation" in result:
            valid_recs = ["APPROVE", "MODIFY", "REJECT", "ERROR"]
            if result["recommendation"] not in valid_recs:
                errors.append(f"Invalid recommendation: {result['recommendation']}")

        if "key_findings" in result and not isinstance(result["key_findings"], list):
            errors.append("key_findings must be a list")

        return len(errors) == 0, errors

    def evaluate_prompt(self, prompt: str, prompt_name: str) -> dict:
        """
        Run all test cases against a prompt with detailed logging.

        Args:
            prompt: The prompt template to evaluate
            prompt_name: Label for this prompt (e.g., "CURRENT", "PROPOSED")

        Returns:
            Dict with accuracy, coverage, format_compliance, and details
        """
        df = self.load_golden_dataset()
        if df.empty:
            return {
                "accuracy": 0.0,
                "coverage": 0.0,
                "format_compliance": 0.0,
                "details": [],
                "error": "No golden dataset found"
            }

        self.logger.log_section(f"EVALUATING: {prompt_name}")

        results = []
        recommendation_matches = 0
        coverage_scores = []
        format_valid_count = 0

        for idx, row in df.iterrows():
            case_id = row["case_id"]
            contract_file = row["contract_file"]
            expected_rec = row["expected_recommendation"]
            expected_findings = row["expected_findings"]
            assertions = row["assertions"]

            self.logger.log(
                f"EVAL:{prompt_name}:{case_id}",
                f"Testing {case_id}...",
                detail=f"Contract: {contract_file}\n"
                       f"Expected recommendation: {expected_rec}\n"
                       f"Expected findings: {expected_findings}\n"
                       f"Assertions: {assertions}"
            )

            # Load contract text
            contract_path = os.path.join(BASE_DIR, contract_file)
            try:
                with open(contract_path, 'r') as f:
                    contract_text = f.read()
            except FileNotFoundError:
                self.logger.log(
                    f"EVAL:{prompt_name}:{case_id}:ERROR",
                    f"Contract file not found: {contract_file}"
                )
                continue

            # Run the prompt
            result = self._run_prompt_on_contract(prompt, contract_text)
            actual_rec = result.get("recommendation", "ERROR")
            actual_findings = result.get("key_findings", [])

            # Check recommendation match
            rec_match = actual_rec == expected_rec
            if rec_match:
                recommendation_matches += 1

            # Check coverage
            coverage = self._calculate_coverage(expected_findings, actual_findings)
            coverage_scores.append(coverage)

            # Check format
            format_valid, format_errors = self._check_format_compliance(result)
            if format_valid:
                format_valid_count += 1

            # Check assertions
            assertions_passed, assertion_details = self._check_assertions(assertions, actual_findings)

            # Determine overall pass/fail
            passed = rec_match and format_valid and assertions_passed

            case_result = {
                "case_id": case_id,
                "passed": passed,
                "recommendation_match": rec_match,
                "expected_recommendation": expected_rec,
                "actual_recommendation": actual_rec,
                "coverage": coverage,
                "format_valid": format_valid,
                "format_errors": format_errors,
                "assertions_passed": assertions_passed,
                "assertion_details": assertion_details,
                "actual_findings": actual_findings
            }
            results.append(case_result)

            # Log result
            status = "PASS" if passed else "FAIL"
            self.logger.log(
                f"EVAL:{prompt_name}:{case_id}:RESULT",
                f"[{status}] {case_id} - Rec: {actual_rec} (expected {expected_rec})",
                detail=f"Recommendation match: {rec_match}\n"
                       f"Expected recommendation: {expected_rec}\n"
                       f"Actual recommendation: {actual_rec}\n\n"
                       f"Coverage: {coverage:.0%}\n"
                       f"Expected findings: {expected_findings}\n"
                       f"Actual findings: {actual_findings}\n\n"
                       f"Format valid: {format_valid}\n"
                       f"Format errors: {format_errors}\n\n"
                       f"Assertions: {assertion_details}\n\n"
                       f"Full response:\n{json.dumps(result, indent=2)}"
            )

        # Calculate aggregate metrics
        total = len(results)
        accuracy = recommendation_matches / total if total > 0 else 0.0
        avg_coverage = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
        format_compliance = format_valid_count / total if total > 0 else 0.0

        self.logger.log(
            f"EVAL:{prompt_name}:SUMMARY",
            f"Accuracy: {accuracy:.0%}, Coverage: {avg_coverage:.0%}, Format: {format_compliance:.0%}",
            detail=f"Total test cases: {total}\n"
                   f"Recommendation matches: {recommendation_matches}\n"
                   f"Format valid: {format_valid_count}\n"
                   f"Average coverage: {avg_coverage:.0%}"
        )

        return {
            "accuracy": accuracy,
            "coverage": avg_coverage,
            "format_compliance": format_compliance,
            "details": results,
            "total_cases": total,
            "passed_cases": sum(1 for r in results if r["passed"])
        }

    def compare_prompts(self, old_prompt: str, new_prompt: str) -> dict:
        """
        Compare two prompts and return comparison metrics.

        Returns:
            Dict with old_results, new_results, and improvement deltas
        """
        self.logger.log_section("PROMPT COMPARISON")

        old_results = self.evaluate_prompt(old_prompt, "CURRENT")
        new_results = self.evaluate_prompt(new_prompt, "PROPOSED")

        improvement = {
            "accuracy_delta": new_results["accuracy"] - old_results["accuracy"],
            "coverage_delta": new_results["coverage"] - old_results["coverage"],
            "format_delta": new_results["format_compliance"] - old_results["format_compliance"]
        }

        self.logger.log(
            "EVAL:COMPARISON",
            "Comparison complete",
            detail=f"CURRENT:  Accuracy={old_results['accuracy']:.0%}, "
                   f"Coverage={old_results['coverage']:.0%}, "
                   f"Format={old_results['format_compliance']:.0%}\n"
                   f"PROPOSED: Accuracy={new_results['accuracy']:.0%}, "
                   f"Coverage={new_results['coverage']:.0%}, "
                   f"Format={new_results['format_compliance']:.0%}\n"
                   f"CHANGE:   Accuracy={improvement['accuracy_delta']:+.0%}, "
                   f"Coverage={improvement['coverage_delta']:+.0%}, "
                   f"Format={improvement['format_delta']:+.0%}"
        )

        return {
            "old": old_results,
            "new": new_results,
            "improvement": improvement
        }
