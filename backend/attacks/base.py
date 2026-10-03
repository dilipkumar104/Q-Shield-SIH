"""Attack simulation base class and registry."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
from quantum import QuantumState


class Attack(ABC):
    """Abstract base class for quantum attacks."""

    def __init__(self, attack_type: str, intensity: float = 0.5):
        """Initialize attack.

        Args:
            attack_type: Type of attack
            intensity: Attack strength (0.0 - 1.0)
        """
        self.attack_type = attack_type
        self.intensity = max(0.0, min(1.0, intensity))

    @abstractmethod
    def apply(self, state: QuantumState, seed: int | None = None) -> QuantumState:
        """Apply attack to quantum state.

        Args:
            state: Input quantum state
            seed: Random seed for reproducibility

        Returns:
            Attacked quantum state
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of attack."""
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.attack_type}(intensity={self.intensity:.2f})"


class ForgeryAttack(Attack):
    """Forgery attack: Create invalid signature that may pass verification."""

    def __init__(self, intensity: float = 0.5, forgery_type: str = "random"):
        """Initialize forgery attack.

        Args:
            intensity: How far from legitimate (0=identical, 1=completely wrong)
            forgery_type: "random", "biased", "bit_flip", "phase_flip"
        """
        super().__init__("forgery", intensity)
        self.forgery_type = forgery_type

    def apply(self, state: QuantumState, seed: int | None = None) -> QuantumState:
        """Create forged state.

        Args:
            state: Legitimate state
            seed: Random seed

        Returns:
            Forged state
        """
        if seed is not None:
            np.random.seed(seed)

        α, β = state.state_vector

        if self.forgery_type == "random":
            # Random state
            theta = np.random.uniform(0, 2 * np.pi)
            new_vector = np.array([np.cos(theta / 2), np.sin(theta / 2) * np.exp(1j * np.random.uniform(0, 2 * np.pi))], dtype=complex)

        elif self.forgery_type == "biased":
            # Biased towards |0⟩ or |1⟩
            if np.random.random() < 0.5:
                new_vector = np.array([1 - self.intensity, self.intensity], dtype=complex)
            else:
                new_vector = np.array([self.intensity, 1 - self.intensity], dtype=complex)

        elif self.forgery_type == "bit_flip":
            # Flip bits
            new_vector = np.array([β * self.intensity + α * (1 - self.intensity),
                                   α * self.intensity + β * (1 - self.intensity)], dtype=complex)

        elif self.forgery_type == "phase_flip":
            # Flip phase
            new_vector = np.array([α, -β * self.intensity + β * (1 - self.intensity)], dtype=complex)

        else:
            raise ValueError(f"Unknown forgery type: {self.forgery_type}")

        # Normalize
        norm = np.linalg.norm(new_vector)
        if norm > 0:
            new_vector = new_vector / norm

        return QuantumState(new_vector, name=f"Forged_{state.name}")

    def get_description(self) -> str:
        """Get description of attack."""
        return f"Forgery ({self.forgery_type}): Intensity {self.intensity:.2f}"


class ImpersonationAttack(Attack):
    """Impersonation attack: Unauthorized party impersonates legitimate signer."""

    def __init__(self, intensity: float = 0.5):
        """Initialize impersonation attack.

        Args:
            intensity: How close to legitimate (0=random, 1=perfect)
        """
        super().__init__("impersonation", intensity)

    def apply(self, state: QuantumState, seed: int | None = None) -> QuantumState:
        """Create impersonated state.

        Args:
            state: Legitimate state
            seed: Random seed

        Returns:
            Impersonated state
        """
        if seed is not None:
            np.random.seed(seed)

        α, β = state.state_vector

        # Blend legitimate state with random guess
        # 0 intensity = random, 1 intensity = perfect
        theta = np.random.uniform(0, 2 * np.pi)
        random_vector = np.array([np.cos(theta / 2), np.sin(theta / 2) * np.exp(1j * np.random.uniform(0, 2 * np.pi))], dtype=complex)

        # Blend
        blended = self.intensity * np.array([α, β], dtype=complex) + (1 - self.intensity) * random_vector

        # Normalize
        norm = np.linalg.norm(blended)
        if norm > 0:
            blended = blended / norm

        return QuantumState(blended, name=f"Impersonated_{state.name}")

    def get_description(self) -> str:
        """Get description of attack."""
        return f"Impersonation: Success probability {self.intensity:.2f}"


class ReplayAttack(Attack):
    """Replay attack: Reuse previously captured signature."""

    def __init__(self, intensity: float = 1.0):
        """Initialize replay attack.

        Args:
            intensity: Not used for replay (always 1.0 = perfect replay)
        """
        super().__init__("replay", 1.0)
        self.original_run_id: str | None = None
        self.replay_session_id: str | None = None

    def set_replay_context(self, original_run_id: str, replay_session_id: str | None = None) -> None:
        """Set replay context.

        Args:
            original_run_id: Run ID to replay
            replay_session_id: Different session ID (if None, same as original)
        """
        self.original_run_id = original_run_id
        self.replay_session_id = replay_session_id or original_run_id

    def apply(self, state: QuantumState, seed: int | None = None) -> QuantumState:
        """Apply replay attack (state unchanged, but flagged).

        Args:
            state: Input state
            seed: Random seed

        Returns:
            Same state (replay uses captured measurement results)
        """
        # Replay attack doesn't modify the quantum state
        # Instead, it reuses previous measurement results
        return QuantumState(state.state_vector, name=f"Replayed_{state.name}")

    def get_description(self) -> str:
        """Get description of attack."""
        return f"Replay: Original {self.original_run_id}, Session {self.replay_session_id}"


class ChannelManipulationAttack(Attack):
    """Channel manipulation: Controlled disturbance to quantum channel."""

    def __init__(self, intensity: float = 0.5, manipulation_type: str = "bit_flip"):
        """Initialize channel manipulation attack.

        Args:
            intensity: Error probability (0.0 - 1.0)
            manipulation_type: "bit_flip", "phase_flip", "depolarizing"
        """
        super().__init__("channel", intensity)
        self.manipulation_type = manipulation_type

    def apply(self, state: QuantumState, seed: int | None = None) -> QuantumState:
        """Apply channel manipulation.

        Args:
            state: Input state
            seed: Random seed

        Returns:
            Manipulated state
        """
        if seed is not None:
            np.random.seed(seed)

        α, β = state.state_vector

        if self.manipulation_type == "bit_flip":
            # X gate with probability intensity
            if np.random.random() < self.intensity:
                new_vector = np.array([β, α], dtype=complex)
            else:
                new_vector = np.array([α, β], dtype=complex)

        elif self.manipulation_type == "phase_flip":
            # Z gate with probability intensity
            if np.random.random() < self.intensity:
                new_vector = np.array([α, -β], dtype=complex)
            else:
                new_vector = np.array([α, β], dtype=complex)

        elif self.manipulation_type == "depolarizing":
            # With probability intensity, replace with maximally mixed state
            # ρ → (1-p)ρ + p(I/2)
            if np.random.random() < self.intensity:
                # Maximally mixed state
                new_vector = np.array([1, 0], dtype=complex) / np.sqrt(2)
            else:
                new_vector = np.array([α, β], dtype=complex)

        else:
            raise ValueError(f"Unknown manipulation type: {self.manipulation_type}")

        return QuantumState(new_vector, name=f"Manipulated_{state.name}")

    def get_description(self) -> str:
        """Get description of attack."""
        return f"Channel {self.manipulation_type}: Error rate {self.intensity:.2f}"


class AttackRegistry:
    """Registry for attack types."""

    _registry: Dict[str, type[Attack]] = {
        "forgery": ForgeryAttack,
        "impersonation": ImpersonationAttack,
        "replay": ReplayAttack,
        "channel": ChannelManipulationAttack,
    }

    @classmethod
    def register(cls, name: str, attack_class: type[Attack]) -> None:
        """Register an attack class."""
        cls._registry[name] = attack_class

    @classmethod
    def get(cls, name: str) -> type[Attack]:
        """Get attack class by name."""
        if name not in cls._registry:
            raise ValueError(f"Unknown attack: {name}. Available: {list(cls._registry.keys())}")
        return cls._registry[name]

    @classmethod
    def list_attacks(cls) -> list[str]:
        """List all registered attacks."""
        return list(cls._registry.keys())

    @classmethod
    def create(cls, attack_type: str, **kwargs) -> Attack:
        """Create attack instance.

        Args:
            attack_type: Type of attack
            **kwargs: Attack-specific parameters

        Returns:
            Attack instance
        """
        attack_class = cls.get(attack_type)
        return attack_class(**kwargs)
