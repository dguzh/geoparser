Feature: Choose a spaCy model for recognition

  The module guide offers en_core_web_trf as the accurate alternative to the
  default small model. Its transformer component comes from a spaCy plugin, and
  when that plugin is missing spaCy reports a missing custom component, which
  reads as a fault in the caller's own code (dguzh/geoparser#128).

  Scenario: A caller builds a recognizer on a small model
    Given the spaCy model "en_core_web_sm" loads
    When I build a recognizer on "en_core_web_sm"
    Then the recognizer is ready to use

  Scenario: A caller builds a recognizer on a transformer model without the plugin
    Given the spaCy model "en_core_web_trf" needs the missing transformer plugin
    When I build a recognizer on "en_core_web_trf"
    Then I am told to install "spacy-curated-transformers"
    And I am still shown the original spaCy error
