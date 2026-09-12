Feature: Size a reference's context to the encoder's budget

  A resolver cannot hand a whole document to an encoder that truncates past
  its maximum sequence length. It keeps the sentences around the reference
  that the budget can pay for, so the place name is always described by the
  text nearest to it rather than by whatever happened to come first.

  Scenario: A short document is used whole
    Given a document whose sentences cost 2, 2, 2 tokens
    And the encoder can afford 10 tokens
    When I size the context around the sentence at index 1
    Then the context covers sentences 0 to 2
    And the context costs at most 10 tokens

  Scenario: A long document is trimmed around the reference
    Given a document whose sentences cost 3, 3, 3, 3, 3 tokens
    And the encoder can afford 9 tokens
    When I size the context around the sentence at index 2
    Then the context covers sentences 1 to 3
    And the context costs at most 9 tokens

  Scenario: Preceding text is preferred when only one neighbour fits
    Given a document whose sentences cost 4, 2, 4 tokens
    And the encoder can afford 6 tokens
    When I size the context around the sentence at index 1
    Then the context covers sentences 0 to 1

  Scenario: A reference near the start grows in the only direction available
    Given a document whose sentences cost 2, 2, 2, 2 tokens
    And the encoder can afford 6 tokens
    When I size the context around the sentence at index 0
    Then the context covers sentences 0 to 2

  Scenario: An oversized sentence is still returned rather than dropped
    Given a document whose sentences cost 2, 50, 2 tokens
    And the encoder can afford 10 tokens
    When I size the context around the sentence at index 1
    Then the context covers sentences 1 to 1

  Scenario: A reference outside every sentence is reported
    Given a document whose sentences cost 2, 2 tokens
    And the encoder can afford 10 tokens
    When I size the context around an offset past the end of the document
    Then sizing fails because no sentence contains the reference
