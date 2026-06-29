"""
Error Handling and Recovery - Robust error handling for LangGraph agents
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from .state import AgentState, AgentType
from .profiles import get_agent_profile

logger = logging.getLogger("agent_error_handler")


class ErrorType(str, Enum):
    """Types of errors that can occur"""
    TIMEOUT = "timeout"
    RETRY_EXCEEDED = "retry_exceeded"
    INTENT_DRIFT = "intent_drift"
    LOOP_DETECTED = "loop_detected"
    LOW_CONFIDENCE = "low_confidence"
    HUMAN_REQUIRED = "human_required"
    SYSTEM_ERROR = "system_error"
    CONTEXT_OVERFLOW = "context_overflow"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext:
    """Context for error handling"""

    def __init__(
        self,
        error_type: ErrorType,
        severity: ErrorSeverity,
        message: str,
        agent: AgentType,
        session_id: str,
        context: Dict[str, Any] = None
    ):
        self.error_type = error_type
        self.severity = severity
        self.message = message
        self.agent = agent
        self.session_id = session_id
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)
        self.attempt_count = 0
        self.recovery_actions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "agent": self.agent.value,
            "session_id": self.session_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "attempt_count": self.attempt_count,
            "recovery_actions": self.recovery_actions,
        }


class ErrorHandler:
    """Centralized error handling and recovery"""

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 30):
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.error_history: List[ErrorContext] = []
        self.recovery_strategies = self._initialize_recovery_strategies()

    def _initialize_recovery_strategies(self) -> Dict[ErrorType, Callable]:
        """Initialize recovery strategies for each error type"""
        return {
            ErrorType.TIMEOUT: self._handle_timeout,
            ErrorType.RETRY_EXCEEDED: self._handle_retry_exceeded,
            ErrorType.INTENT_DRIFT: self._handle_intent_drift,
            ErrorType.LOOP_DETECTED: self._handle_loop_detected,
            ErrorType.LOW_CONFIDENCE: self._handle_low_confidence,
            ErrorType.HUMAN_REQUIRED: self._handle_human_required,
            ErrorType.SYSTEM_ERROR: self._handle_system_error,
            ErrorType.CONTEXT_OVERFLOW: self._handle_context_overflow,
        }

    def handle_error(
        self,
        error: Exception,
        state: AgentState,
        context: Dict[str, Any] = None
    ) -> ErrorContext:
        """Handle error and return error context"""
        # Determine error type and severity
        error_type = self._classify_error(error)
        severity = self._determine_severity(error_type, state)

        # Create error context
        error_context = ErrorContext(
            error_type=error_type,
            severity=severity,
            message=str(error),
            agent=state["current_agent"],
            session_id=state["session_id"],
            context=context or {}
        )

        # Log error
        self._log_error(error_context)

        # Add to history
        self.error_history.append(error_context)

        # Determine recovery action
        recovery_action = self._determine_recovery(error_context, state)

        # Update error context
        error_context.recovery_actions.append(recovery_action)
        error_context.attempt_count += 1

        return error_context

    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type"""
        error_str = str(error).lower()

        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT
        elif "retry" in error_str or "attempts" in error_str:
            return ErrorType.RETRY_EXCEEDED
        elif "loop" in error_str or "circular" in error_str:
            return ErrorType.LOOP_DETECTED
        elif "confidence" in error_str or "uncertain" in error_str:
            return ErrorType.LOW_CONFIDENCE
        elif "human" in error_str or "supervisor" in error_str:
            return ErrorType.HUMAN_REQUIRED
        elif "context" in error_str and "overflow" in error_str:
            return ErrorType.CONTEXT_OVERFLOW
        else:
            return ErrorType.SYSTEM_ERROR

    def _determine_severity(self, error_type: ErrorType, state: AgentState) -> ErrorSeverity:
        """Determine error severity"""
        if error_type in [ErrorType.HUMAN_REQUIRED, ErrorType.SYSTEM_ERROR]:
            return ErrorSeverity.HIGH
        elif error_type in [ErrorType.LOOP_DETECTED, ErrorType.CONTEXT_OVERFLOW]:
            return ErrorSeverity.MEDIUM
        elif error_type == ErrorType.RETRY_EXCEEDED:
            return ErrorSeverity.HIGH if state.get("attempt_count", 0) > self.max_retries else ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with appropriate level"""
        log_message = f"[ErrorHandler] {error_context.severity.value.upper()}: {error_context.message}"

        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _determine_recovery(self, error_context: ErrorContext, state: AgentState) -> str:
        """Determine recovery action"""
        # Check if we should escalate to supervisor
        if error_context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            return "escalate_to_supervisor"

        # Check if we should retry
        if error_context.attempt_count < self.max_retries:
            return "retry_with_adjusted_params"

        # Check if we should reset conversation
        if error_context.error_type == ErrorType.LOOP_DETECTED:
            return "reset_conversation"

        # Check if we should switch agent
        if error_context.error_type == ErrorType.INTENT_DRIFT:
            return "switch_agent"

        # Default fallback
        return "fallback_response"

    def _handle_timeout(self, error_context: ErrorContext) -> str:
        """Handle timeout errors"""
        logger.info(f"[ErrorHandler] Timeout handling for {error_context.agent}")
        return "retry_with_longer_timeout"

    def _handle_retry_exceeded(self, error_context: ErrorContext) -> str:
        """Handle retry exceeded errors"""
        logger.warning(f"[ErrorHandler] Retry exceeded for {error_context.agent}")
        return "escalate_to_supervisor"

    def _handle_intent_drift(self, error_context: ErrorContext) -> str:
        """Handle intent drift errors"""
        logger.info(f"[ErrorHandler] Intent drift detected for {error_context.agent}")
        return "switch_agent"

    def _handle_loop_detected(self, error_context: ErrorContext) -> str:
        """Handle loop detection errors"""
        logger.warning(f"[ErrorHandler] Loop detected for {error_context.agent}")
        return "reset_conversation"

    def _handle_low_confidence(self, error_context: ErrorContext) -> str:
        """Handle low confidence errors"""
        logger.info(f"[ErrorHandler] Low confidence response from {error_context.agent}")
        return "retry_with_different_approach"

    def _handle_human_required(self, error_context: ErrorContext) -> str:
        """Handle human required errors"""
        logger.info(f"[ErrorHandler] Human required for {error_context.agent}")
        return "escalate_to_supervisor"

    def _handle_system_error(self, error_context: ErrorContext) -> str:
        """Handle system errors"""
        logger.error(f"[ErrorHandler] System error for {error_context.agent}")
        return "fallback_response"

    def _handle_context_overflow(self, error_context: ErrorContext) -> str:
        """Handle context overflow errors"""
        logger.info(f"[ErrorHandler] Context overflow for {error_context.agent}")
        return "trim_context_and_retry"

    def should_escalate(self, state: AgentState) -> bool:
        """Check if conversation should be escalated"""
        # Check recent errors
        recent_errors = [
            e for e in self.error_history[-5:]
            if e.session_id == state["session_id"]
            and e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        ]

        # Check attempt count
        if state.get("attempt_count", 0) >= self.max_retries:
            return True

        # Check for multiple failures
        if len(recent_errors) >= 3:
            return True

        return False

    def get_error_summary(self, session_id: str) -> Dict[str, Any]:
        """Get error summary for session"""
        session_errors = [
            e for e in self.error_history
            if e.session_id == session_id
        ]

        if not session_errors:
            return {"total_errors": 0, "severity_breakdown": {}, "error_types": []}

        severity_breakdown = {}
        error_types = []

        for error in session_errors:
            severity = error.severity.value
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
            error_types.append(error.error_type.value)

        return {
            "total_errors": len(session_errors),
            "severity_breakdown": severity_breakdown,
            "error_types": list(set(error_types)),
            "last_error": session_errors[-1].to_dict() if session_errors else None,
        }


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self) -> None:
        """Record successful operation"""
        if self.state == "half_open":
            self.state = "closed"
        self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"[CircuitBreaker] State changed to open after {self.failure_count} failures")

    def should_allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half_open"
                logger.info("[CircuitBreaker] State changed to half-open")
                return True
            return False

        # half-open state - allow one request to test
        return True

    def get_state(self) -> str:
        """Get current state"""
        return self.state


# Global error handler instance
error_handler = ErrorHandler(max_retries=3, timeout_seconds=30)
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


def get_error_handler() -> ErrorHandler:
    """Get global error handler"""
    return error_handler


def get_circuit_breaker() -> CircuitBreaker:
    """Get global circuit breaker"""
    return circuit_breaker