Feature: Parse a manually annotated place

  Scenario: A caller receives a resolved place from the pipeline
    Given the document "Paris is beautiful."
    And the document has the place span from 0 to 5
    And the place resolves to Andorra feature "3041563"
    When I parse the document with the manual pipeline
    Then the parsed document text is "Paris is beautiful."
    And it contains one place span "Paris"
    And the place identifier is "3041563"
