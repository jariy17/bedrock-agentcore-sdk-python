"""Unified client for AWS Bedrock AgentCore services.

This module provides a thin wrapper around boto3 clients that automatically
routes API operations to the appropriate service (control plane or data plane)
without requiring users to know which service handles which operation.
"""

import logging
from typing import Optional

import boto3

logger = logging.getLogger(__name__)


class UnifiedBedrockAgentCoreClient:
    """Unified client that transparently routes operations between services.

    This client provides a single interface for all Bedrock AgentCore operations,
    automatically routing calls to the appropriate underlying boto3 client:
    - bedrock-agentcore-control (control plane): Resource management operations
    - bedrock-agentcore (data plane): Runtime and data operations

    The client uses lazy initialization - boto3 clients are only created when
    first accessed, minimizing overhead for unused services.

    The routing is fully dynamic - no hardcoded operation lists are maintained.
    The client will attempt to find the requested operation on the control plane
    first, then the data plane, ensuring it always works with the latest AWS APIs.

    Attributes:
        region_name (str): AWS region for all operations

    Example:
        >>> client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
        >>>
        >>> # Memory control plane operation - automatically routed
        >>> memory = client.create_memory(
        ...     name="my-memory",
        ...     eventExpiryDuration=90,
        ...     memoryStrategies=[...]
        ... )
        >>>
        >>> # Memory data plane operation - automatically routed
        >>> event = client.create_event(
        ...     memoryId=memory['id'],
        ...     actorId="user-123",
        ...     sessionId="session-456",
        ...     payload=[...]
        ... )
        >>>
        >>> # Code interpreter control plane - automatically routed
        >>> interpreter = client.create_code_interpreter(
        ...     name="my-interpreter",
        ...     executionRoleArn="arn:aws:iam::..."
        ... )
        >>>
        >>> # Code interpreter data plane - automatically routed
        >>> session = client.start_code_interpreter_session(
        ...     codeInterpreterIdentifier="aws.codeinterpreter.v1"
        ... )
    """

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the unified client.

        Args:
            region_name: AWS region to use. If not provided, uses the default
                boto3 session region or falls back to us-west-2.
        """
        self.region_name = region_name or boto3.Session().region_name or "us-west-2"

        # Lazy initialization - clients created on first access
        self._control_plane_client = None
        self._data_plane_client = None

        logger.info(
            "Initialized UnifiedBedrockAgentCoreClient for region: %s",
            self.region_name
        )

    @property
    def control_plane_client(self):
        """Get or create the control plane boto3 client (lazy initialization)."""
        if self._control_plane_client is None:
            self._control_plane_client = boto3.client(
                "bedrock-agentcore-control",
                region_name=self.region_name
            )
            logger.debug(
                "Created control plane client for region: %s",
                self.region_name
            )
        return self._control_plane_client

    @property
    def data_plane_client(self):
        """Get or create the data plane boto3 client (lazy initialization)."""
        if self._data_plane_client is None:
            self._data_plane_client = boto3.client(
                "bedrock-agentcore",
                region_name=self.region_name
            )
            logger.debug(
                "Created data plane client for region: %s",
                self.region_name
            )
        return self._data_plane_client

    def __getattr__(self, name: str):
        """Dynamically route method calls to the appropriate boto3 client.

        This method enables transparent access to all boto3 client methods by
        checking both clients to find where the operation is defined. The routing
        is fully dynamic with no hardcoded operation lists.

        The search order is:
        1. Try control plane client first (bedrock-agentcore-control)
        2. If not found, try data plane client (bedrock-agentcore)
        3. If not found on either, raise AttributeError

        Args:
            name: The method name being accessed

        Returns:
            A callable method from the appropriate boto3 client

        Raises:
            AttributeError: If the method doesn't exist on either client

        Example:
            # Control plane operation
            client.create_memory(name="test", ...)

            # Data plane operation
            client.create_event(memoryId="mem-123", ...)

            # Browser control plane
            client.create_browser(name="my-browser", ...)

            # Browser data plane
            client.start_browser_session(browserIdentifier="...")
        """
        # Try control plane first (resource management operations)
        try:
            if hasattr(self.control_plane_client, name):
                method = getattr(self.control_plane_client, name)
                logger.debug("Routing '%s' to control plane", name)
                return method
        except Exception as e:
            logger.debug("Error checking control plane for '%s': %s", name, e)

        # Try data plane next (runtime/data operations)
        try:
            if hasattr(self.data_plane_client, name):
                method = getattr(self.data_plane_client, name)
                logger.debug("Routing '%s' to data plane", name)
                return method
        except Exception as e:
            logger.debug("Error checking data plane for '%s': %s", name, e)

        # Method not found on either client
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'. "
            f"Operation '{name}' was not found on either the control plane "
            f"(bedrock-agentcore-control) or data plane (bedrock-agentcore) client. "
            f"\n\nPlease check the boto3 documentation for valid operations:\n"
            f"- Control plane: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html\n"
            f"- Data plane: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore.html"
        )

    def get_client_for_operation(self, operation_name: str):
        """Get the underlying boto3 client that handles a specific operation.

        This method is useful for debugging or when you need direct access to
        the underlying boto3 client for advanced use cases.

        Args:
            operation_name: The name of the operation

        Returns:
            The boto3 client that handles this operation

        Raises:
            ValueError: If the operation is not found on either client

        Example:
            >>> client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
            >>> control_client = client.get_client_for_operation("create_memory")
            >>> data_client = client.get_client_for_operation("create_event")
        """
        # Check control plane first
        if hasattr(self.control_plane_client, operation_name):
            return self.control_plane_client

        # Check data plane next
        if hasattr(self.data_plane_client, operation_name):
            return self.data_plane_client

        # Not found on either
        raise ValueError(
            f"Operation '{operation_name}' not found on either client. "
            f"Check the boto3 documentation for valid operations."
        )
