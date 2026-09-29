@api @user_management @crud
Feature: User Management API
  As an API test engineer
  I want to exercise the CRUD operations of the user management REST API
  So that data integrity is verified automatically.

  Background:
    Given I am connected to the user management API

  @smoke
  Scenario: Fetch an existing user
    When I fetch the user with id 1
    Then the user name should be "Leanne Graham"
    And the user username should be "Bret"
    And the response should contain an email field

  Scenario: Create a new user
    When I create a user with name "Wipro Bot" and email "bot@wipro.test"
    Then the create response should be successful
    And a new user id should be assigned

  @update
  Scenario: Update a user
    When I update user 1's email to "updated@wipro.test"
    Then the update response should be successful

  Scenario: Delete a user
    When I delete the user with id 1
    Then the delete response should be successful
