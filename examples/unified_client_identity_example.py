"""
Identity operations example using UnifiedBedrockAgentCoreClient.

This example demonstrates how to use identity and authentication operations
with the unified client, including workload identity and credential providers.
"""

from bedrock_agentcore import UnifiedBedrockAgentCoreClient

# Initialize the unified client
client = UnifiedBedrockAgentCoreClient(region_name="us-west-2")

print("=== Identity and Authentication Operations ===\n")

# ============================================================================
# WORKLOAD IDENTITY OPERATIONS
# ============================================================================

print("1. Creating Workload Identity (Control Plane)")
print("-" * 60)

# Create a workload identity - automatically routed to control plane
workload_identity = client.create_workload_identity(
    name="my-agent-identity",
    allowedResourceOAuth2ReturnUrls=[
        "https://myapp.example.com/oauth/callback"
    ]
)
print(f"✓ Created workload identity: {workload_identity['name']}")
print(f"  Status: {workload_identity['status']}")
print(f"  ARN: {workload_identity['workloadIdentityArn']}")
print()

# ============================================================================
# GET WORKLOAD IDENTITY (Control Plane)
# ============================================================================

print("2. Getting Workload Identity (Control Plane)")
print("-" * 60)

# Get workload identity details - automatically routed to control plane
identity_details = client.get_workload_identity(
    name="my-agent-identity"
)
print(f"✓ Retrieved workload identity: {identity_details['name']}")
print(f"  Status: {identity_details['status']}")
print(f"  Created: {identity_details['createdAt']}")
print(f"  Last Updated: {identity_details['lastUpdatedAt']}")
print(f"  Allowed OAuth URLs: {identity_details['allowedResourceOAuth2ReturnUrls']}")
print()

# ============================================================================
# LIST WORKLOAD IDENTITIES (Control Plane)
# ============================================================================

print("3. Listing Workload Identities (Control Plane)")
print("-" * 60)

# List all workload identities - automatically routed to control plane
identities = client.list_workload_identities(maxResults=10)
print(f"✓ Found {len(identities.get('workloadIdentities', []))} workload identities:")
for identity in identities.get('workloadIdentities', []):
    print(f"  - {identity['name']} (Status: {identity['status']})")
print()

# ============================================================================
# UPDATE WORKLOAD IDENTITY (Control Plane)
# ============================================================================

print("4. Updating Workload Identity (Control Plane)")
print("-" * 60)

# Update workload identity - automatically routed to control plane
updated_identity = client.update_workload_identity(
    name="my-agent-identity",
    allowedResourceOAuth2ReturnUrls=[
        "https://myapp.example.com/oauth/callback",
        "https://myapp-staging.example.com/oauth/callback"  # Added new URL
    ]
)
print(f"✓ Updated workload identity: {updated_identity['name']}")
print(f"  New OAuth URLs: {updated_identity['allowedResourceOAuth2ReturnUrls']}")
print()

# ============================================================================
# GET WORKLOAD ACCESS TOKEN (Data Plane)
# ============================================================================

print("5. Getting Workload Access Token (Data Plane)")
print("-" * 60)

# Get access token for the workload - automatically routed to data plane
# Note: This requires proper IAM permissions and agent setup
try:
    token_response = client.get_workload_access_token(
        workloadName="my-agent-identity",
        userId="user-12345",  # Optional: specific user context
        # userToken="<oauth-token>"  # Optional: user's OAuth token
        # agentIdentityToken="<agent-token>"  # Optional: agent identity token
    )
    print(f"✓ Retrieved workload access token")
    print(f"  Token type: {token_response.get('tokenType', 'Bearer')}")
    print(f"  Expires in: {token_response.get('expiresIn', 'N/A')} seconds")
    # Don't print the actual token for security
    print(f"  Access token: {token_response['accessToken'][:20]}...")
except Exception as e:
    print(f"⚠ Note: Getting access token may fail without proper setup: {type(e).__name__}")
print()

# ============================================================================
# CREDENTIAL PROVIDER OPERATIONS
# ============================================================================

print("6. Creating OAuth2 Credential Provider (Control Plane)")
print("-" * 60)

# Create OAuth2 credential provider - automatically routed to control plane
oauth_provider = client.create_oauth2_credential_provider(
    name="github-oauth-provider",
    authorizationUrl="https://github.com/login/oauth/authorize",
    clientId="my-github-client-id",
    clientSecretArn="arn:aws:secretsmanager:us-west-2:123456789012:secret:github-oauth-secret",
    oAuth2GrantType="AUTHORIZATION_CODE",
    scopes=["read:user", "repo"],
    tokenUrl="https://github.com/login/oauth/access_token"
)
print(f"✓ Created OAuth2 credential provider: {oauth_provider['name']}")
print(f"  Provider ARN: {oauth_provider['credentialProviderArn']}")
print()

print("7. Creating API Key Credential Provider (Control Plane)")
print("-" * 60)

# Create API key provider - automatically routed to control plane
apikey_provider = client.create_api_key_credential_provider(
    name="external-api-provider",
    apiKeySecretArn="arn:aws:secretsmanager:us-west-2:123456789012:secret:external-api-key"
)
print(f"✓ Created API key credential provider: {apikey_provider['name']}")
print(f"  Provider ARN: {apikey_provider['credentialProviderArn']}")
print()

print("8. Listing Credential Providers (Control Plane)")
print("-" * 60)

# List credential providers - automatically routed to control plane
providers = client.list_credential_providers(maxResults=10)
print(f"✓ Found {len(providers.get('credentialProviders', []))} credential providers:")
for provider in providers.get('credentialProviders', []):
    print(f"  - {provider['name']} (Type: {provider['credentialProviderType']})")
print()

print("9. Getting Credential Provider Details (Control Plane)")
print("-" * 60)

# Get credential provider - automatically routed to control plane
provider_details = client.get_credential_provider(
    name="github-oauth-provider"
)
print(f"✓ Retrieved credential provider: {provider_details['name']}")
print(f"  Type: {provider_details['credentialProviderType']}")
print(f"  Status: {provider_details['status']}")
print()

print("10. Getting API Key (Data Plane)")
print("-" * 60)

# Get API key from provider - automatically routed to data plane
try:
    api_key_response = client.get_api_key(
        providerName="external-api-provider",
        # agentIdentityToken="<token>"  # Optional: agent identity token
    )
    print(f"✓ Retrieved API key")
    # Don't print the actual key for security
    print(f"  API key: {api_key_response['apiKey'][:10]}...")
except Exception as e:
    print(f"⚠ Note: Getting API key may fail without proper setup: {type(e).__name__}")
print()

# ============================================================================
# COMPLETE AUTHENTICATION FLOW EXAMPLE
# ============================================================================

print("11. Complete Authentication Flow")
print("-" * 60)
print("Here's how these operations work together:\n")
print("Step 1: Create workload identity (control plane)")
print("  → client.create_workload_identity(...)")
print()
print("Step 2: Get workload identity details (control plane)")
print("  → client.get_workload_identity(name='my-identity')")
print()
print("Step 3: Get access token for agent (data plane)")
print("  → client.get_workload_access_token(workloadName='my-identity')")
print()
print("Step 4: Use token to access resources or get API keys")
print("  → client.get_api_key(providerName='my-provider', agentIdentityToken='...')")
print()

# ============================================================================
# CLEANUP
# ============================================================================

print("12. Cleanup (Control Plane)")
print("-" * 60)

# Delete credential providers - automatically routed to control plane
client.delete_credential_provider(name="github-oauth-provider")
print("✓ Deleted OAuth2 credential provider")

client.delete_credential_provider(name="external-api-provider")
print("✓ Deleted API key credential provider")

# Delete workload identity - automatically routed to control plane
client.delete_workload_identity(name="my-agent-identity")
print("✓ Deleted workload identity")
print()

# ============================================================================
# KEY TAKEAWAYS
# ============================================================================

print("=" * 60)
print("✨ KEY TAKEAWAYS")
print("=" * 60)
print()
print("1. All identity operations work through the SAME unified client")
print("2. Control plane operations (create, get, update, delete) are")
print("   automatically routed to bedrock-agentcore-control")
print("3. Data plane operations (get tokens, get keys) are automatically")
print("   routed to bedrock-agentcore")
print("4. You don't need to know or care which service handles which operation!")
print()
print("Control Plane Operations (automatically routed):")
print("  • create_workload_identity")
print("  • get_workload_identity ← GetWorkloadIdentity command")
print("  • update_workload_identity")
print("  • delete_workload_identity")
print("  • list_workload_identities")
print("  • create_oauth2_credential_provider")
print("  • create_api_key_credential_provider")
print("  • get_credential_provider")
print("  • list_credential_providers")
print("  • delete_credential_provider")
print()
print("Data Plane Operations (automatically routed):")
print("  • get_workload_access_token")
print("  • get_api_key")
print()
print("=" * 60)
