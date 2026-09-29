@api @authentication
Feature: API Authentication

  Background:
    Given I have API clients ready

  @bearer
  Scenario: Bearer token is required
    When I request the bearer endpoint without a token
    Then the request should be rejected with status 401

  Scenario: Valid bearer token authenticates the request
    When I request the bearer endpoint with the token "testtoken"
    Then the request should be authenticated
    And the echoed token should be "testtoken"

  @basic
  Scenario: Basic authentication succeeds for known credentials
    When I request basic auth for user "alice" with password "secret"
    Then the request should be authenticated
    And the authenticated user should be "alice"

  Scenario: Basic authentication fails for wrong password
    When I request basic auth for user "alice" with password "wrong"
    Then the request should be rejected with status 401
