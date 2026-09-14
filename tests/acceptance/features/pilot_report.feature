Feature: Evaluate pilot evidence

  Scenario: A correctly resolved Andorran capital scores perfectly
    Given the pilot observed "Andorra la Vella is the capital of Andorra."
    And the gold place is "Andorra la Vella" with identifier "3041563"
    And the predicted place is "Andorra la Vella" with identifier "3041563"
    When I build the pilot report
    Then the report recognition F1 is 1.0
    And the report resolution accuracy is 1.0
    And the report preserves the span text "Andorra la Vella"
