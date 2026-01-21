"""Tests for UnifiedBedrockAgentCoreClient."""

from unittest.mock import Mock, PropertyMock, patch

import pytest

from bedrock_agentcore.unified_client import UnifiedBedrockAgentCoreClient


class TestUnifiedClientInit:
    """Tests for UnifiedBedrockAgentCoreClient initialization."""

    def test_init_with_explicit_region(self):
        """Test initialization with explicit region."""
        client = UnifiedBedrockAgentCoreClient(region_name="us-east-1")
        assert client.region_name == "us-east-1"

    @patch("boto3.Session")
    def test_init_with_default_region_from_session(self, mock_session):
        """Test initialization uses boto3 session default region."""
        mock_session_instance = Mock()
        mock_session_instance.region_name = "eu-west-1"
        mock_session.return_value = mock_session_instance

        client = UnifiedBedrockAgentCoreClient()
        assert client.region_name == "eu-west-1"

    @patch("boto3.Session")
    def test_init_fallback_to_us_west_2(self, mock_session):
        """Test initialization falls back to us-west-2 when no region available."""
        mock_session_instance = Mock()
        mock_session_instance.region_name = None
        mock_session.return_value = mock_session_instance

        client = UnifiedBedrockAgentCoreClient()
        assert client.region_name == "us-west-2"

    def test_clients_not_initialized_on_init(self):
        """Test that boto3 clients are not created during initialization."""
        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
        assert client._control_plane_client is None
        assert client._data_plane_client is None


class TestLazyClientInitialization:
    """Tests for lazy initialization of boto3 clients."""

    @patch("boto3.client")
    def test_control_plane_client_lazy_init(self, mock_boto_client):
        """Test control plane client is created on first access."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Client should not be created yet
        assert client._control_plane_client is None

        # Access the property
        result = client.control_plane_client

        # Should have created the client
        mock_boto_client.assert_called_once_with(
            "bedrock-agentcore-control",
            region_name="us-west-2"
        )
        assert result == mock_client
        assert client._control_plane_client == mock_client

    @patch("boto3.client")
    def test_control_plane_client_cached(self, mock_boto_client):
        """Test control plane client is cached after first access."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Access twice
        result1 = client.control_plane_client
        result2 = client.control_plane_client

        # Should only create once
        assert mock_boto_client.call_count == 1
        assert result1 == result2

    @patch("boto3.client")
    def test_data_plane_client_lazy_init(self, mock_boto_client):
        """Test data plane client is created on first access."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Client should not be created yet
        assert client._data_plane_client is None

        # Access the property
        result = client.data_plane_client

        # Should have created the client
        mock_boto_client.assert_called_once_with(
            "bedrock-agentcore",
            region_name="us-west-2"
        )
        assert result == mock_client
        assert client._data_plane_client == mock_client

    @patch("boto3.client")
    def test_data_plane_client_cached(self, mock_boto_client):
        """Test data plane client is cached after first access."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Access twice
        result1 = client.data_plane_client
        result2 = client.data_plane_client

        # Should only create once
        assert mock_boto_client.call_count == 1
        assert result1 == result2


class TestOperationRouting:
    """Tests for automatic operation routing."""

    @patch("boto3.client")
    def test_routes_control_plane_operation(self, mock_boto_client):
        """Test that control plane operations are routed correctly."""
        # Setup mock control plane client with create_memory operation
        mock_control_client = Mock()
        mock_control_method = Mock(return_value={"memory": {"id": "mem-123"}})
        mock_control_client.create_memory = mock_control_method

        # Setup mock data plane client
        mock_data_client = Mock()

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Call a control plane operation
        result = client.create_memory(name="test-memory")

        # Should route to control plane
        mock_control_method.assert_called_once_with(name="test-memory")
        assert result == {"memory": {"id": "mem-123"}}

    @patch("boto3.client")
    def test_routes_data_plane_operation(self, mock_boto_client):
        """Test that data plane operations are routed correctly."""
        # Setup mock control plane client
        mock_control_client = Mock()
        mock_control_client.configure_mock(**{"create_event": None})

        # Setup mock data plane client with create_event operation
        mock_data_client = Mock()
        mock_data_method = Mock(return_value={"event": {"eventId": "evt-123"}})
        mock_data_client.create_event = mock_data_method

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Call a data plane operation
        result = client.create_event(memoryId="mem-123", actorId="user-1")

        # Should route to data plane
        mock_data_method.assert_called_once_with(memoryId="mem-123", actorId="user-1")
        assert result == {"event": {"eventId": "evt-123"}}

    @patch("boto3.client")
    def test_raises_error_for_unknown_operation(self, mock_boto_client):
        """Test that unknown operations raise AttributeError."""
        mock_control_client = Mock(spec=[])  # No methods
        mock_data_client = Mock(spec=[])  # No methods

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Try to call non-existent operation
        with pytest.raises(AttributeError) as exc_info:
            client.non_existent_operation()

        assert "non_existent_operation" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestGetClientForOperation:
    """Tests for get_client_for_operation method."""

    @patch("boto3.client")
    def test_returns_control_plane_for_control_operation(self, mock_boto_client):
        """Test returns control plane client for control operations."""
        mock_control_client = Mock()
        mock_control_client.create_memory = Mock()
        mock_data_client = Mock()

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
        result = client.get_client_for_operation("create_memory")

        assert result == mock_control_client

    @patch("boto3.client")
    def test_returns_data_plane_for_data_operation(self, mock_boto_client):
        """Test returns data plane client for data operations."""
        mock_control_client = Mock(spec=[])
        mock_data_client = Mock()
        mock_data_client.create_event = Mock()

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
        result = client.get_client_for_operation("create_event")

        assert result == mock_data_client

    @patch("boto3.client")
    def test_raises_error_for_unknown_operation(self, mock_boto_client):
        """Test raises ValueError for unknown operations."""
        mock_control_client = Mock(spec=[])
        mock_data_client = Mock(spec=[])

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        with pytest.raises(ValueError) as exc_info:
            client.get_client_for_operation("unknown_operation")

        assert "unknown_operation" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestMultipleOperations:
    """Tests for calling multiple operations on the same client."""

    @patch("boto3.client")
    def test_can_call_both_control_and_data_operations(self, mock_boto_client):
        """Test that both control and data plane operations work on same client."""
        # Setup mocks
        mock_control_client = Mock()
        mock_control_client.create_memory = Mock(return_value={"memory": {"id": "mem-123"}})

        mock_data_client = Mock()
        mock_data_client.create_event = Mock(return_value={"event": {"eventId": "evt-123"}})

        def mock_client_factory(service, **kwargs):
            if service == "bedrock-agentcore-control":
                return mock_control_client
            elif service == "bedrock-agentcore":
                return mock_data_client
            return Mock()

        mock_boto_client.side_effect = mock_client_factory

        client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

        # Call control plane operation
        memory_result = client.create_memory(name="test")
        assert memory_result == {"memory": {"id": "mem-123"}}

        # Call data plane operation
        event_result = client.create_event(memoryId="mem-123")
        assert event_result == {"event": {"eventId": "evt-123"}}

        # Both should have been called
        mock_control_client.create_memory.assert_called_once()
        mock_data_client.create_event.assert_called_once()
