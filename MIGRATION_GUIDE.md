# Migration Guide: MemoryClient and IdentityClient Deprecation

This document provides detailed migration instructions for deprecated operations in `MemoryClient` and `IdentityClient`:

- **MemoryClient**: All operations are deprecated. Migrate to `UnifiedBedrockAgentCoreClient` (control plane) and `MemorySessionManager` (data plane).
- **IdentityClient**: Simple boto3 wrapper methods are deprecated. **For OAuth flows (`get_token()`, `get_api_key()`), migrate to auth decorators** from `bedrock_agentcore.identity.auth` (`@requires_access_token`, `@requires_api_key`).
- **CodeInterpreter & BrowserClient**: ⚠️ **NOT deprecated** - see [Why CodeInterpreter and BrowserClient Are NOT Deprecated](#why-codeinterpreter-and-browserclient-are-not-deprecated)

## Table of Contents

**Legend:**
- ✅ **Good Migration** - Direct 1:1 replacement, simple parameter changes
- ⚠️ **Iffy Migration** - Requires manual work (polling, payload construction, helper functions)
- ❌ **No Alternative** - No direct replacement available

---

- [Why CodeInterpreter and BrowserClient Are NOT Deprecated](#why-codeinterpreter-and-browserclient-are-not-deprecated)

- [MemoryClient Migration](#memoryclient-migration)
  - [Control Plane Operations](#control-plane-operations)
    - ✅ [`create_memory()`](#create_memory)
    - ⚠️ [`create_memory_and_wait()`](#create_memory_and_wait)
    - ✅ [`get_memory()`](#get_memory)
    - ✅ [`list_memories()`](#list_memories)
    - ✅ [`update_memory()`](#update_memory)
    - ✅ [`delete_memory()`](#delete_memory)
    - ⚠️ [`delete_memory_and_wait()`](#delete_memory_and_wait)
    - ⚠️ [`create_or_get_memory()`](#create_or_get_memory)
  - [Data Plane Operations](#data-plane-operations)
    - ✅ [`create_event()`](#create_event)
    - ✅ [`get_event()`](#get_event)
    - ✅ [`list_events()`](#list_events)
    - ✅ [`delete_event()`](#delete_event)
    - ✅ [`retrieve_memory_records()` / `retrieve_memories()`](#retrieve_memory_records--retrieve_memories)
    - ✅ [`get_memory_record()`](#get_memory_record)
    - ✅ [`list_memory_records()`](#list_memory_records)
    - ✅ [`delete_memory_record()`](#delete_memory_record)
  - [Strategy Management Operations](#strategy-management-operations)
    - ⚠️ [`add_semantic_strategy()`](#add_semantic_strategy)
    - ⚠️ [`add_semantic_strategy_and_wait()`](#add_semantic_strategy_and_wait)
    - ⚠️ [`add_summary_strategy()`](#add_summary_strategy)
    - ⚠️ [`add_summary_strategy_and_wait()`](#add_summary_strategy_and_wait)
    - ⚠️ [`add_user_preference_strategy()`](#add_user_preference_strategy)
    - ⚠️ [`add_user_preference_strategy_and_wait()`](#add_user_preference_strategy_and_wait)
    - ⚠️ [`modify_strategy()`](#modify_strategy)
    - ⚠️ [`delete_strategy()`](#delete_strategy)
    - ✅ [`update_memory_strategies()`](#update_memory_strategies)
    - ⚠️ [`update_memory_strategies_and_wait()`](#update_memory_strategies_and_wait)
  - [Conversation Helper Operations](#conversation-helper-operations)
    - ✅ [`save_conversation()`](#save_conversation)
    - ✅ [`save_turn()`](#save_turn)
    - ✅ [`process_turn_with_llm()`](#process_turn_with_llm)
    - ✅ [`get_last_k_turns()`](#get_last_k_turns)
    - ✅ [`list_branches()`](#list_branches)
    - ❌ [`get_conversation_tree()`](#get_conversation_tree)
    - ✅ [`fork_conversation()`](#fork_conversation)
    - ⚠️ [`wait_for_memories()`](#wait_for_memories)
- [IdentityClient Migration](#identityclient-migration)
  - [Workload Identity Operations](#workload-identity-operations)
    - ✅ [`create_workload_identity()`](#create_workload_identity)
    - ✅ [`get_workload_identity()`](#get_workload_identity)
    - ✅ [`update_workload_identity()`](#update_workload_identity)
    - ✅ [`delete_workload_identity()`](#delete_workload_identity)
    - ✅ [`list_workload_identities()`](#list_workload_identities)
  - [Credential Provider Operations](#credential-provider-operations)
    - ✅ [`create_oauth2_credential_provider()`](#create_oauth2_credential_provider)
    - ✅ [`create_api_key_credential_provider()`](#create_api_key_credential_provider)
    - ✅ [`get_credential_provider()`](#get_credential_provider)
    - ✅ [`list_credential_providers()`](#list_credential_providers)
    - ✅ [`delete_credential_provider()`](#delete_credential_provider)
  - [Token Operations](#token-operations)
    - ✅ [`get_workload_access_token()`](#get_workload_access_token)
    - ✅ [`get_api_key()`](#get_api_key)
    - ⚠️ [`get_token()`](#get_token)
- [Summary Tables](#summary-tables)
- [Quick Reference: Helper Functions](#quick-reference-helper-functions)
- [Appendix: When OAuth Decorators Are NOT Sufficient](#appendix-when-oauth-decorators-are-not-sufficient)

---

## Why CodeInterpreter and BrowserClient Are NOT Deprecated

**`CodeInterpreter` and `BrowserClient` will remain fully supported and are NOT being deprecated.**

### Why These Clients Are Different

Unlike `MemoryClient` and `IdentityClient` (which are thin wrappers around boto3 clients), `CodeInterpreter` and `BrowserClient` are **stateful clients** that maintain active session state:

**State Maintained:**
- `identifier` - Current interpreter/browser identifier
- `session_id` - Active session ID
- Additional session context (e.g., uploaded files in CodeInterpreter)

### Stateful Workflow Example

**With CodeInterpreter (Stateful):**
```python
client = CodeInterpreter('us-west-2')
client.start()                    # Creates session, stores state

# All operations use stored session state automatically
client.execute_code("x = 5")      # No need to pass identifier/session_id
client.execute_code("print(x)")   # Variables persist (same session)
client.upload_file("data.csv", content)
result = client.execute_code("import pandas; df = pd.read_csv('data.csv')")

client.stop()                     # Cleanup
```

**Without Stateful Client (using UnifiedClient):**
```python
# Customer must manually track and pass state everywhere
session = client.start_code_interpreter_session(codeInterpreterIdentifier="aws.codeinterpreter.v1")
identifier = session['codeInterpreterIdentifier']
session_id = session['sessionId']

# Every call requires passing state
client.invoke_code_interpreter(
    codeInterpreterIdentifier=identifier,  # Must pass
    sessionId=session_id,                   # Must pass
    method="execute",
    parameters={"code": "x = 5"}
)

client.invoke_code_interpreter(
    codeInterpreterIdentifier=identifier,  # Must pass again
    sessionId=session_id,                   # Must pass again
    method="execute",
    parameters={"code": "print(x)"}
)

# Customer must remember to cleanup
client.stop_code_interpreter_session(
    codeInterpreterIdentifier=identifier,
    sessionId=session_id
)
```

### Key Features That Cannot Be Replaced

**CodeInterpreter:**
1. **Session state management** - Automatic tracking of identifier/session_id
2. **Auto-start logic** - Automatically starts session if not active
3. **File I/O helpers** - Base64 encoding/decoding, file metadata tracking
4. **Package management** - `install_packages()` constructs pip install commands
5. **Context management** - `with code_session() as client:` for automatic cleanup
6. **Execution helpers** - `execute_code()`, `execute_command()` with language parameter handling

**BrowserClient:**
1. **Session state management** - Automatic tracking of identifier/session_id
2. **WebSocket authentication** - `generate_ws_headers()` with SigV4 signing (~50 lines of complex logic)
3. **Presigned URLs** - `generate_live_view_url()` with SigV4QueryAuth (~40 lines)
4. **Stream control** - `take_control()` / `release_control()` helpers
5. **Context management** - `with browser_session() as client:` for automatic cleanup

### Value Proposition

These clients save customers **hundreds of lines of boilerplate** per application:
- ~150+ lines for session state management
- ~100+ lines for file I/O with encoding (CodeInterpreter)
- ~90+ lines for WebSocket SigV4 signing (BrowserClient)
- ~40+ lines for presigned URL generation (BrowserClient)

**Recommendation: Continue using `CodeInterpreter` and `BrowserClient` as-is. No migration needed.**

---

## MemoryClient Migration

### Control Plane Operations

#### `create_memory()`

**Before (MemoryClient):**
```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-west-2")
memory = client.create_memory(
    name="my-memory",
    strategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}],
    event_expiry_duration=90
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
memory = client.create_memory(
    name="my-memory",
    memoryStrategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}],
    eventExpiryDuration=90
)
```

**Migration Notes:**
- Change parameter name: `strategies` → `memoryStrategies`
- Change parameter name: `event_expiry_duration` → `eventExpiryDuration`
- Direct 1:1 replacement

---

#### `create_memory_and_wait()`

**Before (MemoryClient):**
```python
memory = client.create_memory_and_wait(
    name="my-memory",
    strategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}],
    max_wait=300
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient
import time

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Create memory
memory = client.create_memory(
    name="my-memory",
    memoryStrategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}]
)
memory_id = memory['memory']['id']

# Poll for ACTIVE status
def wait_for_active(client, memory_id, max_wait=300):
    start = time.time()
    while time.time() - start < max_wait:
        resp = client.get_memory(memoryId=memory_id)
        status = resp['memory']['status']
        if status == 'ACTIVE':
            return resp
        elif status == 'FAILED':
            raise RuntimeError(f"Memory failed: {resp['memory'].get('failureReason')}")
        time.sleep(10)
    raise TimeoutError("Memory not ACTIVE in time")

memory = wait_for_active(client, memory_id, max_wait=300)
```

**Migration Notes:**
- Need to implement polling logic yourself (~50 lines)
- Consider creating a reusable helper function
- Check for both ACTIVE and FAILED states

---

#### `get_memory()`

**Before (MemoryClient):**
```python
memory = client.get_memory(memory_id="mem-123")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
memory = client.get_memory(memoryId="mem-123")
```

**Migration Notes:**
- Change parameter name: `memory_id` → `memoryId`
- Direct 1:1 replacement

---

#### `list_memories()`

**Before (MemoryClient):**
```python
memories = client.list_memories(max_results=10, next_token=None)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
memories = client.list_memories(maxResults=10, nextToken=None)
```

**Migration Notes:**
- Change parameter name: `max_results` → `maxResults`
- Change parameter name: `next_token` → `nextToken`
- Direct 1:1 replacement

---

#### `update_memory()`

**Before (MemoryClient):**
```python
updated = client.update_memory(
    memory_id="mem-123",
    strategies_to_add=[{"SUMMARY": {"name": "summaries"}}],
    strategies_to_modify=[...],
    strategies_to_delete=["old-strategy"]
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[{"SUMMARY": {"name": "summaries"}}],
    memoryStrategiesToModify=[...],
    memoryStrategiesToDelete=["old-strategy"]
)
```

**Migration Notes:**
- Change parameter names to camelCase
- Direct 1:1 replacement

---

#### `delete_memory()`

**Before (MemoryClient):**
```python
client.delete_memory(memory_id="mem-123")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
client.delete_memory(memoryId="mem-123")
```

**Migration Notes:**
- Change parameter name: `memory_id` → `memoryId`
- Direct 1:1 replacement

---

#### `delete_memory_and_wait()`

**Before (MemoryClient):**
```python
client.delete_memory_and_wait(memory_id="mem-123", max_wait=300)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
client.delete_memory(memoryId="mem-123")

# Poll to confirm deletion
def wait_for_deletion(client, memory_id, max_wait=300):
    import time
    from botocore.exceptions import ClientError

    start = time.time()
    while time.time() - start < max_wait:
        try:
            client.get_memory(memoryId=memory_id)
            time.sleep(5)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return  # Successfully deleted
            raise
    raise TimeoutError("Memory not deleted in time")

wait_for_deletion(client, "mem-123", max_wait=300)
```

**Migration Notes:**
- Need to implement deletion polling yourself
- Check for ResourceNotFoundException
- Consider creating a reusable helper function

---

#### `create_or_get_memory()`

**Before (MemoryClient):**
```python
memory = client.create_or_get_memory(
    name="my-memory",
    strategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}]
)
```

**After (UnifiedBedrockAgentCoreClient + Logic):**
```python
from botocore.exceptions import ClientError

def create_or_get_memory(client, name, strategies):
    try:
        # Try to create
        return client.create_memory(name=name, memoryStrategies=strategies)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConflictException':
            # Already exists, get it
            memories = client.list_memories()
            for mem in memories.get('memories', []):
                if mem['name'] == name:
                    return client.get_memory(memoryId=mem['id'])
        raise

memory = create_or_get_memory(
    client,
    name="my-memory",
    strategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}]
)
```

**Migration Notes:**
- Need to implement error handling logic
- Handle ConflictException for existing resources
- Consider creating a reusable helper function

---

### Data Plane Operations

#### `create_event()`

**Before (MemoryClient):**
```python
event = client.create_event(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    payload=[{"conversational": {"content": {"text": "Hello"}, "role": "USER"}}]
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
from bedrock_agentcore.memory import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
event = manager.add_turns(
    actor_id="user-1",
    session_id="sess-1",
    messages=[ConversationalMessage("Hello", MessageRole.USER)]
)
```

**Alternative (UnifiedBedrockAgentCoreClient - Raw):**
```python
from datetime import datetime, timezone

event = client.create_event(
    memoryId="mem-123",
    actorId="user-1",
    sessionId="sess-1",
    eventTimestamp=datetime.now(timezone.utc),
    payload=[{"conversational": {"content": {"text": "Hello"}, "role": "USER"}}]
)
```

**Migration Notes:**
- **Prefer MemorySessionManager** for cleaner API with dataclasses
- UnifiedClient requires manual timestamp and payload construction
- MemorySessionManager handles memory_id injection automatically

---

#### `get_event()`

**Before (MemoryClient):**
```python
event = client.get_event(memory_id="mem-123", event_id="evt-456")
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
event = manager.get_event(eventId="evt-456")
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
event = client.get_event(memoryId="mem-123", eventId="evt-456")
```

**Migration Notes:**
- MemorySessionManager auto-injects memory_id
- UnifiedClient requires explicit memory_id

---

#### `list_events()`

**Before (MemoryClient):**
```python
events = client.list_events(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    max_results=50
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
events = manager.list_events(
    actorId="user-1",
    sessionId="sess-1",
    maxResults=50
)
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
events = client.list_events(
    memoryId="mem-123",
    actorId="user-1",
    sessionId="sess-1",
    maxResults=50
)
```

**Migration Notes:**
- MemorySessionManager returns typed Event objects
- MemorySessionManager handles pagination automatically

---

#### `delete_event()`

**Before (MemoryClient):**
```python
client.delete_event(memory_id="mem-123", event_id="evt-456")
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
manager.delete_event(eventId="evt-456")
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
client.delete_event(memoryId="mem-123", eventId="evt-456")
```

---

#### `retrieve_memory_records()` / `retrieve_memories()`

**Before (MemoryClient):**
```python
records = client.retrieve_memories(
    memory_id="mem-123",
    namespace="app/user-1/sess-1",
    query="search query",
    top_k=5
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
from bedrock_agentcore.memory.constants import RetrievalConfig

manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
records = manager.search_long_term_memories(
    searchQuery="search query",
    namespace="app/user-1/sess-1",
    topK=5
)
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
records = client.retrieve_memory_records(
    memoryId="mem-123",
    namespace="app/user-1/sess-1",
    searchCriteria={"searchQuery": "search query", "topK": 5}
)
```

**Migration Notes:**
- MemorySessionManager has better method naming (`search_long_term_memories`)
- MemorySessionManager returns typed MemoryRecord objects
- UnifiedClient requires searchCriteria dict

---

#### `get_memory_record()`

**Before (MemoryClient):**
```python
record = client.get_memory_record(
    memory_id="mem-123",
    memory_record_id="rec-456"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
record = manager.get_memory_record(memoryRecordId="rec-456")
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
record = client.get_memory_record(memoryId="mem-123", memoryRecordId="rec-456")
```

---

#### `list_memory_records()`

**Before (MemoryClient):**
```python
records = client.list_memory_records(
    memory_id="mem-123",
    namespace="app/user-1"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
records = manager.list_long_term_memory_records(namespace="app/user-1")
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
records = client.list_memory_records(memoryId="mem-123", namespace="app/user-1")
```

**Migration Notes:**
- MemorySessionManager handles pagination automatically
- MemorySessionManager returns typed MemoryRecord objects

---

#### `delete_memory_record()`

**Before (MemoryClient):**
```python
client.delete_memory_record(
    memory_id="mem-123",
    memory_record_id="rec-456"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
manager.delete_memory_record(memoryRecordId="rec-456")
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
client.delete_memory_record(memoryId="mem-123", memoryRecordId="rec-456")
```

---

### Strategy Management Operations

#### `add_semantic_strategy()`

**Before (MemoryClient):**
```python
updated = client.add_semantic_strategy(
    memory_id="mem-123",
    strategy_name="facts",
    namespaces=["app/{actorId}/{sessionId}"]
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
strategy = {
    "SEMANTIC": {
        "name": "facts",
        "namespaces": ["app/{actorId}/{sessionId}"]
    }
}
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)
```

**Migration Notes:**
- Need to construct strategy dict manually
- Use update_memory with memoryStrategiesToAdd

---

#### `add_semantic_strategy_and_wait()`

**Before (MemoryClient):**
```python
updated = client.add_semantic_strategy_and_wait(
    memory_id="mem-123",
    strategy_name="facts",
    namespaces=["app/{actorId}/{sessionId}"],
    max_wait=300
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
strategy = {
    "SEMANTIC": {
        "name": "facts",
        "namespaces": ["app/{actorId}/{sessionId}"]
    }
}
client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)

# Use wait_for_active helper from earlier
wait_for_active(client, "mem-123", max_wait=300)
```

**Migration Notes:**
- Combine update_memory with polling helper
- Check for ACTIVE status after strategy addition

---

#### `add_summary_strategy()`

**Before (MemoryClient):**
```python
updated = client.add_summary_strategy(
    memory_id="mem-123",
    strategy_name="summaries"
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
strategy = {
    "SUMMARY": {
        "name": "summaries"
    }
}
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)
```

---

#### `add_summary_strategy_and_wait()`

**Before (MemoryClient):**
```python
updated = client.add_summary_strategy_and_wait(
    memory_id="mem-123",
    strategy_name="summaries",
    max_wait=300
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
strategy = {
    "SUMMARY": {
        "name": "summaries"
    }
}
client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)
wait_for_active(client, "mem-123", max_wait=300)
```

---

#### `add_user_preference_strategy()`

**Before (MemoryClient):**
```python
updated = client.add_user_preference_strategy(
    memory_id="mem-123",
    strategy_name="preferences"
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
strategy = {
    "USER_PREFERENCE": {
        "name": "preferences"
    }
}
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)
```

---

#### `add_user_preference_strategy_and_wait()`

**Before (MemoryClient):**
```python
updated = client.add_user_preference_strategy_and_wait(
    memory_id="mem-123",
    strategy_name="preferences",
    max_wait=300
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
strategy = {
    "USER_PREFERENCE": {
        "name": "preferences"
    }
}
client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[strategy]
)
wait_for_active(client, "mem-123", max_wait=300)
```

---

#### `modify_strategy()`

**Before (MemoryClient):**
```python
updated = client.modify_strategy(
    memory_id="mem-123",
    strategy_name="facts",
    new_config={"namespaces": ["new/namespace"]}
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
strategy_to_modify = {
    "SEMANTIC": {
        "name": "facts",
        "namespaces": ["new/namespace"]
    }
}
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToModify=[strategy_to_modify]
)
```

---

#### `delete_strategy()`

**Before (MemoryClient):**
```python
updated = client.delete_strategy(
    memory_id="mem-123",
    strategy_name="facts"
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToDelete=["facts"]
)
```

---

#### `update_memory_strategies()`

**Before (MemoryClient):**
```python
updated = client.update_memory_strategies(
    memory_id="mem-123",
    strategies_to_add=[{"SEMANTIC": {"name": "new-facts", "namespaces": ["app"]}}],
    strategies_to_modify=[{"SUMMARY": {"name": "summaries"}}],
    strategies_to_delete=["old-strategy"]
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[{"SEMANTIC": {"name": "new-facts", "namespaces": ["app"]}}],
    memoryStrategiesToModify=[{"SUMMARY": {"name": "summaries"}}],
    memoryStrategiesToDelete=["old-strategy"]
)
```

**Migration Notes:**
- Direct 1:1 replacement with parameter name changes

---

#### `update_memory_strategies_and_wait()`

**Before (MemoryClient):**
```python
updated = client.update_memory_strategies_and_wait(
    memory_id="mem-123",
    strategies_to_add=[{"SEMANTIC": {"name": "new-facts", "namespaces": ["app"]}}],
    max_wait=300
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
updated = client.update_memory(
    memoryId="mem-123",
    memoryStrategiesToAdd=[{"SEMANTIC": {"name": "new-facts", "namespaces": ["app"]}}]
)
wait_for_active(client, "mem-123", max_wait=300)
```

---

### Conversation Helper Operations

#### `save_conversation()`

**Before (MemoryClient):**
```python
event = client.save_conversation(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    messages=[
        ("What's the weather?", "USER"),
        ("It's sunny!", "ASSISTANT")
    ]
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
from bedrock_agentcore.memory import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
event = manager.add_turns(
    actor_id="user-1",
    session_id="sess-1",
    messages=[
        ConversationalMessage("What's the weather?", MessageRole.USER),
        ConversationalMessage("It's sunny!", MessageRole.ASSISTANT)
    ]
)
```

**Alternative (UnifiedBedrockAgentCoreClient - NOT RECOMMENDED):**
```python
from datetime import datetime, timezone

payload = []
for text, role in messages:
    payload.append({
        "conversational": {
            "content": {"text": text},
            "role": role.upper()
        }
    })

event = client.create_event(
    memoryId="mem-123",
    actorId="user-1",
    sessionId="sess-1",
    eventTimestamp=datetime.now(timezone.utc),
    payload=payload
)
```

**Migration Notes:**
- **Strongly prefer MemorySessionManager** for this operation
- MemorySessionManager uses typed dataclasses instead of tuples
- UnifiedClient requires ~15 lines of manual payload construction

---

#### `save_turn()`

**Before (MemoryClient):**
```python
event = client.save_turn(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    user_message="What's the weather?",
    assistant_message="It's sunny!"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
from bedrock_agentcore.memory import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
event = manager.add_turns(
    actor_id="user-1",
    session_id="sess-1",
    messages=[
        ConversationalMessage("What's the weather?", MessageRole.USER),
        ConversationalMessage("It's sunny!", MessageRole.ASSISTANT)
    ]
)
```

**Migration Notes:**
- Use add_turns with two messages
- More flexible than save_turn (supports multiple turns)

---

#### `process_turn_with_llm()`

**Before (MemoryClient):**
```python
memories, response, event = client.process_turn_with_llm(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    user_input="What's the weather?",
    llm_callback=my_llm_function,
    retrieval_namespace="app/weather",
    top_k=3
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
from bedrock_agentcore.memory import MemorySessionManager
from bedrock_agentcore.memory.constants import RetrievalConfig

manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
memories, response, event = manager.process_turn_with_llm(
    actor_id="user-1",
    session_id="sess-1",
    user_input="What's the weather?",
    llm_callback=my_llm_function,
    retrieval_config={
        "app/weather": RetrievalConfig(top_k=3, relevance_score=0.5)
    }
)

# BONUS: Async version!
memories, response, event = await manager.process_turn_with_llm_async(
    actor_id="user-1",
    session_id="sess-1",
    user_input="What's the weather?",
    llm_callback=my_async_llm_function,
    retrieval_config={
        "app/weather": RetrievalConfig(top_k=3)
    }
)
```

**Alternative (UnifiedBedrockAgentCoreClient - NOT RECOMMENDED):**

Not practical - requires ~30+ lines to implement:
1. Call retrieve_memory_records
2. Filter by relevance_score
3. Invoke LLM callback manually
4. Format response messages
5. Call create_event

**Migration Notes:**
- **Must use MemorySessionManager** for this operation
- MemorySessionManager supports multi-namespace retrieval
- MemorySessionManager provides async version
- UnifiedClient requires complete re-implementation

---

#### `get_last_k_turns()`

**Before (MemoryClient):**
```python
turns = client.get_last_k_turns(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    k=5
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
turns = manager.get_last_k_turns(
    actor_id="user-1",
    session_id="sess-1",
    k=5
)
```

**Alternative (UnifiedBedrockAgentCoreClient - NOT RECOMMENDED):**

Requires ~40 lines of implementation:
```python
# 1. List events
events = client.list_events(memoryId="mem-123", actorId="user-1", sessionId="sess-1")

# 2. Group messages into turns (complex logic)
turns = []
current_turn = []
for event in reversed(events.get('events', [])):
    for payload_item in event['payload']:
        if 'conversational' in payload_item:
            role = payload_item['conversational']['role']
            if role == 'USER' and current_turn:
                turns.append(current_turn)
                current_turn = []
                if len(turns) >= k:
                    break
            current_turn.append(payload_item['conversational'])
    if len(turns) >= k:
        break

# ... more complex logic
```

**Migration Notes:**
- **Must use MemorySessionManager** for this operation
- UnifiedClient requires complete re-implementation (~40 lines)

---

#### `list_branches()`

**Before (MemoryClient):**
```python
branches = client.list_branches(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
branches = manager.list_branches(
    actor_id="user-1",
    session_id="sess-1"
)
```

**Alternative (UnifiedBedrockAgentCoreClient - NOT RECOMMENDED):**

Requires ~60 lines of tree-building logic.

**Migration Notes:**
- **Must use MemorySessionManager** for this operation
- UnifiedClient requires complete re-implementation

---

#### `get_conversation_tree()`

**Before (MemoryClient):**
```python
tree = client.get_conversation_tree(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1"
)
```

**After:**

**NOT AVAILABLE** - This method is unique to MemoryClient and has no replacement.

**Workaround (Complex):**
```python
# 1. Use list_branches from MemorySessionManager
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
branches = manager.list_branches(actor_id="user-1", session_id="sess-1")

# 2. Implement tree construction yourself (~80 lines)
# This is complex and requires understanding of the event/branch structure
```

**Migration Notes:**
- This is the ONLY method with no direct replacement
- Consider using list_branches() instead if tree structure is not critical
- May need to implement custom tree-building logic if required

---

#### `fork_conversation()`

**Before (MemoryClient):**
```python
forked_event = client.fork_conversation(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    parent_event_id="evt-456",
    new_branch_id="branch-789"
)
```

**After (MemorySessionManager - RECOMMENDED):**
```python
manager = MemorySessionManager(memory_id="mem-123", region_name="us-west-2")
forked_event = manager.fork_conversation(
    actor_id="user-1",
    session_id="sess-1",
    parentEventId="evt-456",
    branchId="branch-789"
)
```

**Alternative (UnifiedBedrockAgentCoreClient):**
```python
from datetime import datetime, timezone

forked_event = client.create_event(
    memoryId="mem-123",
    actorId="user-1",
    sessionId="sess-1",
    eventTimestamp=datetime.now(timezone.utc),
    parentEventId="evt-456",
    branchId="branch-789",
    payload=[]
)
```

**Migration Notes:**
- MemorySessionManager provides helper method
- UnifiedClient requires manual event creation

---

#### `wait_for_memories()`

**Before (MemoryClient):**
```python
client.wait_for_memories(
    memory_id="mem-123",
    actor_id="user-1",
    session_id="sess-1",
    event_id="evt-456",
    max_wait=60
)
```

**After (UnifiedBedrockAgentCoreClient + Helper):**
```python
def wait_for_memory_extraction(client, memory_id, event_id, max_wait=60):
    import time
    start = time.time()

    while time.time() - start < max_wait:
        event = client.get_event(memoryId=memory_id, eventId=event_id)

        # Check if memory records have been extracted
        records = client.list_memory_records(memoryId=memory_id)
        # Logic to check if extraction is complete...

        time.sleep(5)

    raise TimeoutError("Memory extraction not complete")

wait_for_memory_extraction(client, "mem-123", "evt-456", max_wait=60)
```

**Migration Notes:**
- Need to implement custom polling logic
- Check memory records to verify extraction completion

---

## IdentityClient Migration

### Workload Identity Operations

#### `create_workload_identity()`

**Before (IdentityClient):**
```python
from bedrock_agentcore.services import IdentityClient

client = IdentityClient(region="us-west-2")
identity = client.create_workload_identity(
    name="my-identity",
    allowed_resource_oauth_2_return_urls=["https://app.example.com/callback"]
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")
identity = client.create_workload_identity(
    name="my-identity",
    allowedResourceOAuth2ReturnUrls=["https://app.example.com/callback"]
)
```

**Migration Notes:**
- Change parameter name: `allowed_resource_oauth_2_return_urls` → `allowedResourceOAuth2ReturnUrls`
- Direct 1:1 replacement

---

#### `get_workload_identity()`

**Before (IdentityClient):**
```python
identity = client.get_workload_identity(name="my-identity")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
identity = client.get_workload_identity(name="my-identity")
```

**Migration Notes:**
- Identical API - no changes needed

---

#### `update_workload_identity()`

**Before (IdentityClient):**
```python
identity = client.update_workload_identity(
    name="my-identity",
    allowed_resource_oauth_2_return_urls=[
        "https://app.example.com/callback",
        "https://staging.example.com/callback"
    ]
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
identity = client.update_workload_identity(
    name="my-identity",
    allowedResourceOAuth2ReturnUrls=[
        "https://app.example.com/callback",
        "https://staging.example.com/callback"
    ]
)
```

**Migration Notes:**
- Change parameter name to camelCase
- Direct 1:1 replacement

---

#### `delete_workload_identity()`

**Before (IdentityClient):**
```python
client.delete_workload_identity(name="my-identity")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
client.delete_workload_identity(name="my-identity")
```

**Migration Notes:**
- Identical API - no changes needed

---

#### `list_workload_identities()`

**Before (IdentityClient):**
```python
identities = client.list_workload_identities(max_results=10)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
identities = client.list_workload_identities(maxResults=10)
```

**Migration Notes:**
- Change parameter name: `max_results` → `maxResults`

---

### Credential Provider Operations

#### `create_oauth2_credential_provider()`

**Before (IdentityClient):**
```python
provider = client.create_oauth2_credential_provider({
    "name": "github-oauth",
    "authorizationUrl": "https://github.com/login/oauth/authorize",
    "clientId": "my-client-id",
    "clientSecretArn": "arn:aws:secretsmanager:...",
    "oAuth2GrantType": "AUTHORIZATION_CODE",
    "scopes": ["read:user", "repo"],
    "tokenUrl": "https://github.com/login/oauth/access_token"
})
```

**After (UnifiedBedrockAgentCoreClient):**
```python
provider = client.create_oauth2_credential_provider(
    name="github-oauth",
    authorizationUrl="https://github.com/login/oauth/authorize",
    clientId="my-client-id",
    clientSecretArn="arn:aws:secretsmanager:...",
    oAuth2GrantType="AUTHORIZATION_CODE",
    scopes=["read:user", "repo"],
    tokenUrl="https://github.com/login/oauth/access_token"
)
```

**Migration Notes:**
- Change from dict parameter to keyword arguments
- Direct 1:1 replacement

---

#### `create_api_key_credential_provider()`

**Before (IdentityClient):**
```python
provider = client.create_api_key_credential_provider({
    "name": "external-api",
    "apiKeySecretArn": "arn:aws:secretsmanager:..."
})
```

**After (UnifiedBedrockAgentCoreClient):**
```python
provider = client.create_api_key_credential_provider(
    name="external-api",
    apiKeySecretArn="arn:aws:secretsmanager:..."
)
```

**Migration Notes:**
- Change from dict parameter to keyword arguments
- Direct 1:1 replacement

---

#### `get_credential_provider()`

**Before (IdentityClient):**
```python
provider = client.get_credential_provider(name="github-oauth")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
provider = client.get_credential_provider(name="github-oauth")
```

**Migration Notes:**
- Identical API - no changes needed

---

#### `list_credential_providers()`

**Before (IdentityClient):**
```python
providers = client.list_credential_providers(max_results=10)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
providers = client.list_credential_providers(maxResults=10)
```

**Migration Notes:**
- Change parameter name: `max_results` → `maxResults`

---

#### `delete_credential_provider()`

**Before (IdentityClient):**
```python
client.delete_credential_provider(name="github-oauth")
```

**After (UnifiedBedrockAgentCoreClient):**
```python
client.delete_credential_provider(name="github-oauth")
```

**Migration Notes:**
- Identical API - no changes needed

---

### Token Operations

#### `get_workload_access_token()`

**Before (IdentityClient):**
```python
token = client.get_workload_access_token(
    workload_name="my-identity",
    user_id="user-123"
)
```

**After (UnifiedBedrockAgentCoreClient):**
```python
token = client.get_workload_access_token(
    workloadName="my-identity",
    userId="user-123"
)
```

**Migration Notes:**
- Change parameter names to camelCase
- Direct 1:1 replacement

---

#### `get_api_key()`

**Before (IdentityClient):**
```python
from bedrock_agentcore.services import IdentityClient

client = IdentityClient(region="us-west-2")

# Get API key with async support
api_key = await client.get_api_key(
    provider_name="my-provider",
    agent_identity_token=token
)
```

**After (Recommended - Use decorator):**
```python
from bedrock_agentcore.identity.auth import requires_api_key

# API key with decorator
@requires_api_key(
    provider_name="my-api-provider",
    into="api_key"
)
def call_api(*, api_key: str):
    # API key is automatically injected
    print(f"Got key: {api_key}")
```

**Alternative (For imperative use cases - UnifiedBedrockAgentCoreClient):**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Use Case: Token caching, instance variables, dynamic providers, etc.
api_key = client.get_resource_api_key(
    resourceCredentialProviderName="my-provider",
    workloadIdentityToken="<token>"
)["apiKey"]
```

**Migration Notes:**
- **For most use cases**: Use `@requires_api_key` decorator (simpler, cleaner)
- **For imperative use cases** (caching, instance variables, dynamic providers): Use `UnifiedBedrockAgentCoreClient.get_resource_api_key()`
- Both approaches fully supported - choose based on your needs

---

#### `get_token()`

**Before (IdentityClient):**
```python
from bedrock_agentcore.services import IdentityClient

client = IdentityClient(region="us-west-2")

# OAuth flow with automatic polling
token = await client.get_token(
    workload_name="my-identity",
    user_token="oauth-token",
    on_auth_url=lambda url: print(f"Visit: {url}")
)
```

**After (Recommended - Use decorator):**
```python
from bedrock_agentcore.identity.auth import requires_access_token

# OAuth flow with decorator
@requires_access_token(
    provider_name="my-oauth-provider",
    into="access_token",
    scopes=["read:user"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: print(f"Visit: {url}")
)
def my_function(*, access_token: str):
    # Token is automatically injected
    print(f"Got token: {access_token}")
```

**Migration Notes:**
- **Preferred approach**: Use `@requires_access_token` decorator from `bedrock_agentcore.identity.auth`
- Decorator handles OAuth flow and token polling automatically
- Works with both sync and async functions

**⚠️ Important:** Decorators work by injecting tokens as function parameters (declarative approach). For imperative use cases (token reuse, caching, instance variables, dynamic providers, background workers, etc.), see [Appendix: When OAuth Decorators Are NOT Sufficient](#appendix-when-oauth-decorators-are-not-sufficient) for details on migration options

---

## Summary Tables

### MemoryClient Migration Difficulty

| Operation Type | Method Count | Migration Difficulty | Recommended Approach |
|---------------|--------------|---------------------|---------------------|
| **Control Plane (Simple)** | 5 | Easy | UnifiedBedrockAgentCoreClient |
| **Control Plane (With Polling)** | 3 | Medium | UnifiedClient + Helper Functions |
| **Data Plane (Simple)** | 6 | Easy | MemorySessionManager (preferred) or UnifiedClient |
| **Data Plane (Conversations)** | 5 | Easy | MemorySessionManager (MUST USE) |
| **Strategy Management** | 11 | Medium | UnifiedClient + Manual Strategy Construction |
| **Advanced Helpers** | 5 | Hard | MemorySessionManager (MUST USE) |

### IdentityClient Migration Difficulty

| Operation Type | Method Count | Migration Difficulty | Recommended Approach |
|---------------|--------------|---------------------|---------------------|
| **Workload Identity (Simple)** | 5 | Easy | UnifiedBedrockAgentCoreClient |
| **Credential Providers** | 5 | Easy | UnifiedBedrockAgentCoreClient |
| **Token Operations (Simple)** | 1 | Easy | UnifiedBedrockAgentCoreClient |
| **OAuth Flow (get_token, get_api_key)** | 2 | Easy | **Use auth decorators** (`@requires_access_token`, `@requires_api_key`) |

---

## Quick Reference: Helper Functions

These helper functions ease migration for common patterns:

```python
# helper_functions.py
from bedrock_agentcore import UnifiedBedrockAgentCoreClient
import time
from typing import Dict, Any

def wait_for_memory_active(
    client: UnifiedBedrockAgentCoreClient,
    memory_id: str,
    max_wait: int = 300,
    poll_interval: int = 10
) -> Dict[str, Any]:
    """Poll until memory is ACTIVE."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = client.get_memory(memoryId=memory_id)
        status = response['memory']['status']
        if status == 'ACTIVE':
            return response
        elif status == 'FAILED':
            reason = response['memory'].get('failureReason', 'Unknown')
            raise RuntimeError(f"Memory failed: {reason}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Memory not ACTIVE within {max_wait}s")

def create_memory_and_wait(
    client: UnifiedBedrockAgentCoreClient,
    name: str,
    strategies: list,
    max_wait: int = 300,
    **kwargs
) -> Dict[str, Any]:
    """Create memory and wait for ACTIVE status."""
    memory = client.create_memory(
        name=name,
        memoryStrategies=strategies,
        **kwargs
    )
    memory_id = memory['memory']['id']
    return wait_for_memory_active(client, memory_id, max_wait)

def add_strategy_and_wait(
    client: UnifiedBedrockAgentCoreClient,
    memory_id: str,
    strategy: Dict[str, Any],
    max_wait: int = 300
) -> Dict[str, Any]:
    """Add strategy and wait for ACTIVE status."""
    client.update_memory(
        memoryId=memory_id,
        memoryStrategiesToAdd=[strategy]
    )
    return wait_for_memory_active(client, memory_id, max_wait)
```

**Usage:**
```python
from bedrock_agentcore import UnifiedBedrockAgentCoreClient
from helper_functions import create_memory_and_wait, add_strategy_and_wait

client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

# Create and wait in one call
memory = create_memory_and_wait(
    client,
    name="my-memory",
    strategies=[{"SEMANTIC": {"name": "facts", "namespaces": ["app/{actorId}"]}}]
)

# Add strategy and wait
add_strategy_and_wait(
    client,
    memory_id=memory['memory']['id'],
    strategy={"SUMMARY": {"name": "summaries"}}
)
```

---

## Appendix: When OAuth Decorators Are NOT Sufficient

Decorators work by **injecting tokens as function parameters** (declarative approach). However, you need **imperative** `get_token()` calls when:

### 1. Token Reuse Across Multiple Calls

```python
# ❌ Decorator fetches token 3 times (inefficient)
@requires_access_token(provider_name="github", scopes=["read:user"])
def get_user(): ...

@requires_access_token(provider_name="github", scopes=["read:user"])
def get_repos(): ...

# ✅ Fetch once, reuse (need imperative approach)
token = await identity_client.get_token(provider_name="github", ...)
user = get_user_raw(token)
repos = get_repos_raw(token)
```

### 2. Storing Tokens in Instance Variables

```python
class GitHubClient:
    def __init__(self):
        # Can't use decorator in __init__
        self.token = identity_client.get_token(provider_name="github", ...)

    def get_user(self):
        return api_call(self.token)  # Reuse instance token
```

### 3. Token Caching / Storage

```python
# Store in cache/database for reuse
token = await identity_client.get_token(...)
cache.set(f"token:{user_id}", token, ttl=3600)
```

### 4. Dynamic Provider Selection

```python
# Provider determined at runtime (can't hardcode in decorator)
provider = determine_provider(user)
token = await identity_client.get_token(provider_name=provider, ...)
```

### 5. Conditional Token Fetching

```python
if requires_authentication:
    token = await identity_client.get_token(...)
    return call_with_auth(token)
else:
    return call_without_auth()
```

### 6. Background Tasks / Workers

```python
# No function decoration context
def worker():
    token = identity_client.get_token(...)
    process_jobs(token)
```

### 7. Multiple Tokens for Different Users

```python
for user in users:
    # Can't parameterize decorator per iteration
    token = identity_client.get_token(workload_name=user.workload, ...)
    send_notification(user, token)
```

---

### ⚠️ Deprecation Impact

Since `IdentityClient.get_token()` will be deprecated, **customers with these advanced use cases will lose functionality**.

### Recommendations Before Deprecating

**Option A: Don't deprecate `get_token()`**
- Keep this method available for advanced use cases where decorators don't work
- Decorators are great for 80% of use cases
- Imperative method needed for remaining 20% (token reuse, caching, dynamic providers)

**Option B: Provide imperative helper function**

If deprecating IdentityClient, add utility function:

```python
# In bedrock_agentcore.identity.auth module
async def get_oauth_token(provider_name: str, scopes: List[str], ...) -> str:
    """Get OAuth token imperatively (not decorator).

    Wraps get_resource_oauth2_token with polling logic.
    """
    ...
```

**Option C: Accept limited functionality**
- Document that these advanced patterns are not supported after deprecation

---

### Current Recommendation

- **For most use cases**: Migrate to `@requires_access_token` decorator
- **For imperative use cases**: Migration path TBD - depends on deprecation decision above
