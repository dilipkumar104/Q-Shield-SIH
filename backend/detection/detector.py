"""Statistical hypothesis testing and threat detection."""
import numpy as np
from typing import Dict, Any, Tuple
from scipy import stats


class StatisticalTest:
    """Base statistical test class."""

    def __init__(self, name: str):
        """Initialize test.

        Args:
            name: Test name
        """
        self.name = name

    def test(
        self,
        observed: Dict[str, float],
        expected: Dict[str, float],
        sample_size: int,
    ) -> Dict[str, Any]:
        """Run statistical test.

        Args:
            observed: Observed probability distribution {outcome: probability}
            expected: Expected probability distribution
            sample_size: Number of samples

        Returns:
            Test results dictionary
        """
        raise NotImplementedError


class ChiSquareTest(StatisticalTest):
    """Chi-square goodness-of-fit test."""

    def __init__(self, significance_level: float = 0.05):
        """Initialize chi-square test.

        Args:
            significance_level: Type I error rate (α)
        """
        super().__init__("chi_square")
        self.significance_level = significance_level

    def test(
        self,
        observed: Dict[str, float],
        expected: Dict[str, float],
        sample_size: int,
    ) -> Dict[str, Any]:
        """Run chi-square test.

        H0: Data follows expected distribution
        H1: Data does not follow expected distribution

        Args:
            observed: Observed probabilities
            expected: Expected probabilities
            sample_size: Number of samples

        Returns:
            {
                "statistic": float,
                "p_value": float,
                "degrees_of_freedom": int,
                "critical_value": float,
                "rejects_null": bool,
                "confidence": float,
            }
        """
        # Convert probabilities to counts
        observed_counts = np.array([observed.get(str(i), 0) * sample_size for i in range(2)])
        expected_probs = np.array([expected.get(str(i), 0) for i in range(2)])
        expected_counts = expected_probs * sample_size

        # Chi-square statistic
        # χ² = Σ (O_i - E_i)² / E_i
        chi2_stat = np.sum((observed_counts - expected_counts) ** 2 / (expected_counts + 1e-10))

        # Degrees of freedom
        df = len(observed_counts) - 1

        # P-value
        p_value = 1 - stats.chi2.cdf(chi2_stat, df)

        # Critical value at significance level
        critical_value = stats.chi2.ppf(1 - self.significance_level, df)

        # Confidence
        confidence = 1 - p_value

        return {
            "statistic": float(chi2_stat),
            "p_value": float(p_value),
            "degrees_of_freedom": df,
            "critical_value": float(critical_value),
            "rejects_null": chi2_stat > critical_value,
            "confidence": float(confidence),
        }


class TotalVariationDistanceTest(StatisticalTest):
    """Total variation distance test."""

    def __init__(self, threshold: float = 0.15):
        """Initialize TV distance test.

        Args:
            threshold: Decision threshold
        """
        super().__init__("tv_distance")
        self.threshold = threshold

    def test(
        self,
        observed: Dict[str, float],
        expected: Dict[str, float],
        sample_size: int,
    ) -> Dict[str, Any]:
        """Run TV distance test.

        Total variation distance: TV = (1/2) Σ |P_obs(i) - P_exp(i)|

        Args:
            observed: Observed probabilities
            expected: Expected probabilities
            sample_size: Number of samples (not used for TV)

        Returns:
            {
                "statistic": float,
                "threshold": float,
                "exceeds_threshold": bool,
                "confidence": float,
                "distribution_match": float,
            }
        """
        # Compute TV distance
        tv_distance = 0.5 * sum(abs(observed.get(str(i), 0) - expected.get(str(i), 0)) for i in range(2))

        # Confidence: how far from threshold
        if tv_distance < self.threshold:
            confidence = 1 - (tv_distance / self.threshold)
        else:
            confidence = (tv_distance - self.threshold) / (1 - self.threshold + 1e-10)
            confidence = min(confidence, 1.0)

        # Distribution match (0=different, 1=identical)
        match = 1 - tv_distance

        return {
            "statistic": float(tv_distance),
            "threshold": float(self.threshold),
            "exceeds_threshold": tv_distance > self.threshold,
            "confidence": float(abs(confidence)),
            "distribution_match": float(match),
        }


class SecurityMetrics:
    """Compute security metrics from simulation results."""

    @staticmethod
    def compute_false_accept_rate(
        legitimate_runs: int,
        legitimate_accepted: int,
    ) -> float:
        """Compute false-accept rate (FAR).

        FAR = (legitimate runs rejected) / (total legitimate runs)

        Args:
            legitimate_runs: Total legitimate signature attempts
            legitimate_accepted: Legitimate signatures accepted

        Returns:
            FAR (0 to 1)
        """
        if legitimate_runs == 0:
            return 0.0
        rejected = legitimate_runs - legitimate_accepted
        return rejected / legitimate_runs

    @staticmethod
    def compute_false_reject_rate(
        attack_runs: int,
        attack_detected: int,
    ) -> float:
        """Compute false-reject rate (FRR).

        FRR = (attacks not detected) / (total attacks)

        Args:
            attack_runs: Total attack attempts
            attack_detected: Attacks detected

        Returns:
            FRR (0 to 1)
        """
        if attack_runs == 0:
            return 0.0
        missed = attack_runs - attack_detected
        return missed / attack_runs

    @staticmethod
    def compute_detection_rate(
        attack_runs: int,
        attack_detected: int,
    ) -> float:
        """Compute detection rate (DR).

        DR = (attacks detected) / (total attacks)

        Args:
            attack_runs: Total attack attempts
            attack_detected: Attacks detected

        Returns:
            DR (0 to 1)
        """
        if attack_runs == 0:
            return 0.0
        return attack_detected / attack_runs

    @staticmethod
    def compute_verification_accuracy(
        legitimate_runs: int,
        legitimate_accepted: int,
    ) -> float:
        """Compute verification accuracy.

        VAcc = (legitimate accepted) / (total legitimate)

        Args:
            legitimate_runs: Total legitimate attempts
            legitimate_accepted: Legitimate accepted

        Returns:
            Verification accuracy (0 to 1)
        """
        if legitimate_runs == 0:
            return 0.0
        return legitimate_accepted / legitimate_runs

    @staticmethod
    def compute_forgery_probability(
        attack_runs: int,
        attack_accepted: int,
    ) -> float:
        """Compute forgery probability (FP).

        FP = (attacks accepted as legitimate) / (total attacks)

        Args:
            attack_runs: Total attack attempts
            attack_accepted: Attacks accepted as legitimate

        Returns:
            Forgery probability (0 to 1)
        """
        if attack_runs == 0:
            return 0.0
        return attack_accepted / attack_runs


class ThreatDetector:
    """Main threat detection engine."""

    def __init__(
        self,
        threshold: float = 0.15,
        method: str = "tv_distance",
        significance_level: float = 0.05,
    ):
        """Initialize detector.

        Args:
            threshold: Detection threshold
            method: Statistical method ("chi_square", "tv_distance", "both")
            significance_level: Type I error rate
        """
        self.threshold = threshold
        self.method = method
        self.significance_level = significance_level

        self.chi_square_test = ChiSquareTest(significance_level)
        self.tv_test = TotalVariationDistanceTest(threshold)

    def detect(
        self,
        observed_distribution: Dict[str, float],
        expected_distribution: Dict[str, float],
        sample_size: int,
        attack_type: str | None = None,
    ) -> Dict[str, Any]:
        """Detect threat in measurement distribution.

        Args:
            observed_distribution: Observed measurement probabilities
            expected_distribution: Expected measurement probabilities
            sample_size: Number of samples
            attack_type: If known, the attack type

        Returns:
            Detection result with decision and evidence
        """
        result: Dict[str, Any] = {
            "decision": "LEGITIMATE",
            "attack_type": attack_type,
            "tests": {},
        }

        # Run statistical tests
        if self.method in ("chi_square", "both"):
            chi2_result = self.chi_square_test.test(
                observed_distribution,
                expected_distribution,
                sample_size,
            )
            result["tests"]["chi_square"] = chi2_result
            if chi2_result["rejects_null"]:
                result["decision"] = "ATTACK"

        if self.method in ("tv_distance", "both"):
            tv_result = self.tv_test.test(
                observed_distribution,
                expected_distribution,
                sample_size,
            )
            result["tests"]["tv_distance"] = tv_result
            if tv_result["exceeds_threshold"]:
                result["decision"] = "ATTACK"

        # If using both methods, require both to agree for HIGH confidence
        if self.method == "both":
            chi2_attack = result["tests"]["chi_square"]["rejects_null"]
            tv_attack = result["tests"]["tv_distance"]["exceeds_threshold"]

            if chi2_attack and tv_attack:
                result["decision"] = "ATTACK"
                result["confidence"] = "high"
            elif chi2_attack or tv_attack:
                result["decision"] = "SUSPICIOUS"
                result["confidence"] = "medium"
            else:
                result["decision"] = "LEGITIMATE"
                result["confidence"] = "high"
        else:
            result["confidence"] = "high" if result["decision"] != "LEGITIMATE" else "high"

        return result

    def compute_roc_curve(
        self,
        legitimate_samples: list[Dict[str, float]],
        attack_samples: list[Dict[str, float]],
        expected_distribution: Dict[str, float],
        thresholds: np.ndarray | None = None,
    ) -> Dict[str, Any]:
        """Compute ROC curve for threshold optimization.

        Args:
            legitimate_samples: List of observed distributions from legitimate runs
            attack_samples: List of observed distributions from attack runs
            expected_distribution: Expected distribution
            thresholds: Threshold values to test (default: 0.01 to 0.99)

        Returns:
            ROC curve data
        """
        if thresholds is None:
            thresholds = np.linspace(0.01, 0.99, 50)

        fpr_list = []  # False positive rate
        tpr_list = []  # True positive rate (detection rate)

        for threshold in thresholds:
            detector = ThreatDetector(threshold=threshold, method="tv_distance")

            # Test on legitimate samples (should be accepted)
            legit_detected = 0
            for sample in legitimate_samples:
                result = detector.detect(sample, expected_distribution, 1000)
                if result["decision"] == "ATTACK":
                    legit_detected += 1

            fpr = legit_detected / len(legitimate_samples) if legitimate_samples else 0

            # Test on attack samples (should be detected)
            attacks_detected = 0
            for sample in attack_samples:
                result = detector.detect(sample, expected_distribution, 1000)
                if result["decision"] == "ATTACK":
                    attacks_detected += 1

            tpr = attacks_detected / len(attack_samples) if attack_samples else 0

            fpr_list.append(fpr)
            tpr_list.append(tpr)

        return {
            "thresholds": [float(t) for t in thresholds],
            "fpr": fpr_list,  # False Accept Rate
            "tpr": tpr_list,  # Detection Rate
            "auc": float(np.trapz(tpr_list, fpr_list)),  # Area under curve
        }
