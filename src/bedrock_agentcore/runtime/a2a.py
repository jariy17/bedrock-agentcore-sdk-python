"""A2A protocol support for Bedrock AgentCore Runtime.

Provides Bedrock-specific glue around the official a2a-sdk, handling header
extraction, health checks, and Docker host detection.

Targets a2a-sdk 1.x. The a2a-sdk 1.0 release redesigned the server API: the
``a2a.server.apps`` app-wrapper module was removed in favour of route factories
in ``a2a.server.routes`` (e.g. :func:`create_jsonrpc_routes`) that are attached
directly to a Starlette app. To preserve the wire format and ``AgentCard`` shape
that Bedrock AgentCore agents already depend on (top-level ``url`` field,
snake_case JSON-RPC payloads such as ``message/send``), this module serves the
v0.3-compatible JSON-RPC endpoint (``enable_v0_3_compat=True``) and builds the
agent card from the ``a2a.compat.v0_3`` pydantic models.
"""

import logging
import time
import uuid
from typing import Any, Callable, Optional

from ..config_bundle.baggage import _extract_baggage
from .context import BedrockAgentCoreContext
from .models import (
    _AUTHORIZATION_HEADER_LOWER,
    ACCESS_TOKEN_HEADER,
    AGENTCORE_RUNTIME_URL_ENV,
    AUTHORIZATION_HEADER,
    BAGGAGE_KEY_EXPERIMENT_ARN,
    BAGGAGE_KEY_EXPERIMENT_VARIANT,
    OAUTH2_CALLBACK_URL_HEADER,
    REQUEST_ID_HEADER,
    SESSION_HEADER,
    PingStatus,
    is_forwardable_header,
)
from .tracing import _ensure_baggage_processor_registered

logger = logging.getLogger(__name__)


def _check_a2a_sdk() -> None:
    """Raise ImportError with install instructions if a2a-sdk is missing."""
    try:
        import a2a  # noqa: F401
    except ImportError:
        raise ImportError(
            'a2a-sdk is required for A2A protocol support. Install it with: pip install "bedrock-agentcore[a2a]"'
        ) from None


def _build_agent_card(executor: Any, url: str) -> Any:
    """Build an AgentCard by introspecting a StrandsA2AExecutor.

    Extracts name/description from ``executor.agent``. Falls back to generic
    defaults for other executors. Returns a v0.3-compatible
    ``a2a.compat.v0_3.types.AgentCard`` so the served card keeps a top-level
    ``url`` field, which Bedrock AgentCore clients rely on.

    Args:
        executor: The agent executor to introspect.
        url: The agent invocation URL to advertise in the card.

    Returns:
        An ``a2a.compat.v0_3.types.AgentCard`` instance.
    """
    from a2a.compat.v0_3.types import AgentCapabilities, AgentCard, AgentSkill

    name = "agent"
    description = "A Bedrock AgentCore agent"

    agent = getattr(executor, "agent", None)
    if agent is not None:
        name = getattr(agent, "name", None) or name
        description = getattr(agent, "description", None) or description

    return AgentCard(
        name=name,
        description=description,
        url=url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        skills=[AgentSkill(id="main", name=name, description=description, tags=["main"])],
        default_input_modes=["text"],
        default_output_modes=["text"],
    )


def build_runtime_url(agent_arn: str, region: Optional[str] = None) -> str:
    """Build the Bedrock AgentCore runtime invocation URL from an agent ARN.

    Args:
        agent_arn: The agent runtime ARN, e.g.
            ``arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/my-agent-abc123``.
        region: AWS region override. If ``None``, extracted from the ARN.

    Returns:
        The full invocation URL with the ARN properly URL-encoded.
    """
    from urllib.parse import quote

    from .._utils.endpoints import validate_region

    if region is None:
        # ARN format: arn:aws:bedrock-agentcore:<region>:<account>:runtime/<id>
        parts = agent_arn.split(":")
        if len(parts) >= 4:
            region = parts[3]
        else:
            raise ValueError(f"Cannot extract region from ARN: {agent_arn}")

    validate_region(region)
    encoded_arn = quote(agent_arn, safe="")
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations"


def _make_call_context_builder_base() -> type:
    """Return the a2a-sdk v1.x ``ServerCallContextBuilder`` base class.

    Imported lazily so this module can be imported without a2a-sdk installed.
    """
    from a2a.server.routes import ServerCallContextBuilder

    return ServerCallContextBuilder


class BedrockCallContextBuilder:
    """Extracts Bedrock runtime headers and propagates them into BedrockAgentCoreContext.

    Conforms to the a2a-sdk v1.x ``ServerCallContextBuilder`` interface so the
    A2A JSON-RPC dispatcher calls ``build()`` on every incoming request. It is
    registered as a virtual subclass of that ABC at the bottom of this module so
    ``isinstance`` checks succeed without requiring a2a-sdk to be importable at
    class-definition time.
    """

    def __init__(self) -> None:
        """Initialize BedrockCallContextBuilder and register the baggage span processor."""
        # Register early so the ASGI entry span (POST /invocations) gets stamped.
        _ensure_baggage_processor_registered()

    def build(self, request: Any) -> Any:
        """Build a ServerCallContext from a Starlette Request.

        Args:
            request: A Starlette Request object.

        Returns:
            A ``a2a.server.context.ServerCallContext`` with Bedrock headers
            stored in ``state``.
        """
        from a2a.server.context import ServerCallContext

        headers = request.headers

        request_id = headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        session_id = headers.get(SESSION_HEADER)
        BedrockAgentCoreContext.set_request_context(request_id, session_id)

        workload_access_token = headers.get(ACCESS_TOKEN_HEADER)
        if workload_access_token:
            BedrockAgentCoreContext.set_workload_access_token(workload_access_token)

        oauth2_callback_url = headers.get(OAUTH2_CALLBACK_URL_HEADER)
        if oauth2_callback_url:
            BedrockAgentCoreContext.set_oauth2_callback_url(oauth2_callback_url)

        # Collect forwardable request headers.
        # Authorization is normalised to a canonical key regardless of wire casing
        # (HTTP/2 always lowercases headers; HTTP/1.1 may preserve mixed case).
        # All other headers are checked against the runtime header allowlist rules.
        request_headers: dict[str, str] = {}
        for header_name, header_value in headers.items():
            if header_name.lower() == _AUTHORIZATION_HEADER_LOWER:
                request_headers[AUTHORIZATION_HEADER] = header_value
            elif is_forwardable_header(header_name):
                request_headers[header_name] = header_value
        if request_headers:
            BedrockAgentCoreContext.set_request_headers(request_headers)

        all_baggage: dict = {}
        try:
            all_baggage = _extract_baggage(headers)
        except Exception as e:
            logger.warning(
                "Failed to parse baggage: %s: %s — raw baggage: %r",
                type(e).__name__,
                e,
                headers.get("baggage", ""),
            )
        experiment_arn = next(iter(all_baggage.get(BAGGAGE_KEY_EXPERIMENT_ARN, [])), None)
        experiment_variant = next(iter(all_baggage.get(BAGGAGE_KEY_EXPERIMENT_VARIANT, [])), None)
        BedrockAgentCoreContext.set_routing_experiment(experiment_arn, experiment_variant)
        _ensure_baggage_processor_registered()

        # NOTE (a2a-sdk v1.x): the JSON-RPC dispatcher overwrites
        # ``state["request_id"]`` with the JSON-RPC envelope id *after* this
        # builder runs (see a2a.server.routes.jsonrpc_dispatcher), so the
        # Bedrock runtime request id is also mirrored under a dedicated,
        # non-colliding ``bedrock_request_id`` key. The authoritative
        # propagation path is the ``BedrockAgentCoreContext`` contextvar set
        # via ``set_request_context`` above, which is unaffected.
        state = {
            "request_id": request_id,
            "bedrock_request_id": request_id,
            "session_id": session_id,
        }
        if workload_access_token:
            state["workload_access_token"] = workload_access_token
        if oauth2_callback_url:
            state["oauth2_callback_url"] = oauth2_callback_url

        return ServerCallContext(state=state)


# Register as a virtual subclass of the v1.x ServerCallContextBuilder ABC so
# isinstance checks pass without requiring a2a-sdk to be importable at
# class-definition time.
try:
    _make_call_context_builder_base().register(BedrockCallContextBuilder)
except Exception:  # pragma: no cover
    pass


def build_a2a_app(
    executor: Any,
    agent_card: Any = None,
    *,
    task_store: Any = None,
    context_builder: Any = None,
    ping_handler: Optional[Callable[[], PingStatus]] = None,
) -> Any:
    """Build a Starlette app wired for A2A protocol with Bedrock extras.

    Args:
        executor: An ``AgentExecutor`` that implements the agent logic.
        agent_card: Optional agent card describing the agent. Accepts an
            ``a2a.compat.v0_3.types.AgentCard`` (recommended — keeps the
            top-level ``url`` field) or a v1.x ``a2a.types.AgentCard``. If
            ``None``, one is built automatically by introspecting the executor.
        task_store: Optional ``TaskStore``; defaults to ``InMemoryTaskStore``.
        context_builder: Optional context builder conforming to the v1.x
            ``ServerCallContextBuilder`` interface; defaults to
            ``BedrockCallContextBuilder``.
        ping_handler: Optional callback returning a ``PingStatus``.

    Returns:
        A Starlette application exposing ``/ping``, the A2A JSON-RPC endpoint at
        ``/`` (with v0.3 wire compatibility), and the agent card at
        ``/.well-known/agent-card.json``.
    """
    import os

    _check_a2a_sdk()

    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.routes import create_jsonrpc_routes
    from a2a.server.tasks import InMemoryTaskStore
    from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, DEFAULT_RPC_URL
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    runtime_url = os.environ.get(AGENTCORE_RUNTIME_URL_ENV, "http://localhost:9000/")

    if agent_card is None:
        agent_card = _build_agent_card(executor, runtime_url)
    elif os.environ.get(AGENTCORE_RUNTIME_URL_ENV):
        agent_card.url = runtime_url

    if task_store is None:
        task_store = InMemoryTaskStore()
    if context_builder is None:
        context_builder = BedrockCallContextBuilder()

    # The v1.x request handler and JSON-RPC routes operate on the core (protobuf)
    # AgentCard, so convert if we were handed a v0.3-compatible pydantic card.
    core_card = _to_core_agent_card(agent_card)

    http_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=core_card,
    )

    a2a_routes = create_jsonrpc_routes(
        http_handler,
        DEFAULT_RPC_URL,
        context_builder=context_builder,
        enable_v0_3_compat=True,
    )

    # Serve the agent card in the same shape the supplied card serializes to.
    # For a v0.3 pydantic card this preserves the top-level ``url`` field.
    card_payload = _agent_card_to_dict(agent_card)

    async def _serve_agent_card(request: Any) -> JSONResponse:
        return JSONResponse(card_payload)

    last_status_update_time = time.time()

    def _handle_ping(request: Any) -> JSONResponse:
        nonlocal last_status_update_time
        try:
            if ping_handler is not None:
                status = ping_handler()
            else:
                status = PingStatus.HEALTHY
            last_status_update_time = time.time()
        except Exception:
            logger.exception("Custom ping handler failed, falling back to Healthy")
            status = PingStatus.HEALTHY
        return JSONResponse({"status": status.value, "time_of_last_update": int(last_status_update_time)})

    routes = [
        Route("/ping", _handle_ping, methods=["GET"]),
        Route(AGENT_CARD_WELL_KNOWN_PATH, _serve_agent_card, methods=["GET"]),
        *a2a_routes,
    ]
    return Starlette(routes=routes)


def _to_core_agent_card(agent_card: Any) -> Any:
    """Convert an AgentCard to the v1.x core (protobuf) representation.

    Accepts either an ``a2a.compat.v0_3.types.AgentCard`` (converted via the
    compat layer) or an already-core ``a2a.types.AgentCard`` (returned as-is).
    """
    from a2a.compat.v0_3 import conversions
    from a2a.compat.v0_3.types import AgentCard as CompatAgentCard

    if isinstance(agent_card, CompatAgentCard):
        return conversions.to_core_agent_card(agent_card)
    return agent_card


def _agent_card_to_dict(agent_card: Any) -> dict:
    """Serialize an AgentCard to a JSON-ready dict for the well-known route.

    v0.3 pydantic cards are dumped by alias (preserving the top-level ``url``
    field); core protobuf cards fall back to the SDK helper.
    """
    from a2a.compat.v0_3.types import AgentCard as CompatAgentCard

    if isinstance(agent_card, CompatAgentCard):
        return agent_card.model_dump(mode="json", exclude_none=True, by_alias=True)

    from a2a.server.request_handlers.response_helpers import agent_card_to_dict

    return agent_card_to_dict(agent_card)


def serve_a2a(
    executor: Any,
    agent_card: Any = None,
    *,
    port: int = 9000,
    host: Optional[str] = None,
    task_store: Any = None,
    context_builder: Any = None,
    ping_handler: Optional[Callable[[], PingStatus]] = None,
    **kwargs: Any,
) -> None:
    """Start a Bedrock-compatible A2A server.

    Args:
        executor: An ``AgentExecutor`` that implements the agent logic.
        agent_card: Optional agent card describing the agent. If ``None``, one is
            built automatically by introspecting the executor.
        port: Port to serve on (default 9000).
        host: Host to bind to; auto-detected if ``None``.
        task_store: Optional ``TaskStore``; defaults to ``InMemoryTaskStore``.
        context_builder: Optional context builder; defaults to
            ``BedrockCallContextBuilder``.
        ping_handler: Optional callback returning a ``PingStatus``.
        **kwargs: Additional arguments forwarded to ``uvicorn.run()``.
    """
    import os

    import uvicorn

    app = build_a2a_app(
        executor,
        agent_card,
        task_store=task_store,
        context_builder=context_builder,
        ping_handler=ping_handler,
    )

    if host is None:
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            host = "0.0.0.0"  # nosec B104 - Container needs this to expose the port
        else:
            host = "127.0.0.1"

    uvicorn_params: dict[str, Any] = {
        "host": host,
        "port": port,
        "log_level": "info",
    }
    uvicorn_params.update(kwargs)

    uvicorn.run(app, **uvicorn_params)
