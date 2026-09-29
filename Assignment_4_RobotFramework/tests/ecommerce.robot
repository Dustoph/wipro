*** Settings ***
Library    SeleniumLibrary
Library    ${CURDIR}/../resources/store_resource.py

Suite Setup    Suite Bootstrap
Suite Teardown    Suite Teardown

*** Keywords ***
Suite Bootstrap
    [Documentation]    Open the headless browser for the whole suite.
    Store Open
Suite Teardown
    [Documentation]    Close every browser when the suite finishes.
    Store Close

*** Test Cases ***
Login And Add To Cart
    [Setup]
    Store Login    admin@tutorialsninja.com    123456
    Store Clear Cart
    Store Open Product    40
    Store Add To Cart    2
    Store Verify Cart    40    2
    [Teardown]    Store Logout

Data Driven Product Flows
    [Setup]
    Store Login    admin@tutorialsninja.com    123456
    Store Clear Cart
    ${ROWS}    Store Read Products
    FOR    ${row}    IN    @{ROWS}
        ${pid}    Set Variable    ${row}[0]
        ${qty}    Set Variable    ${row}[1]
        Log    processing product ${pid} quantity ${qty}
        Store Open Product    ${pid}
        Store Add To Cart    ${qty}
    END
    [Teardown]    Store Logout

*** Comments ***
Command line:      robot --outputdir . tests/ecommerce.robot
Jenkins:           see Jenkinsfile (generated alongside this suite).
