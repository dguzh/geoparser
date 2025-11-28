---
title: 'The Irchel Geoparser: A Modular Python Library for Toponym Recognition and Resolution'
tags:
  - Python
  - natural language processing
  - geographic information retrieval
  - geoparsing
  - toponym recognition
  - toponym resolution
authors:
  - name: Diego Gomes
    orcid: 0009-0003-8449-2603
    affiliation: 1
    corresponding: true
  - name: Ross S. Purves
    orcid: 0000-0002-9878-9243
    affiliation: 1
affiliations:
  - name: Department of Geography, University of Zurich, Switzerland
    index: 1
    ror: 02crff812
date: 28 November 2025
bibliography: paper.bib
---

# Summary

The Irchel Geoparser is an open-source Python library for recognising and resolving place names (toponyms) in unstructured text. Based on a modular architecture, it provides an end-to-end geoparsing pipeline in which the components responsible for toponym recognition, toponym resolution, and the underlying gazetteer data can be freely adapted or exchanged. The library includes robust, configurable built-in modules and a GeoNames-based gazetteer configuration, offering strong performance for English text out of the box. Users can also choose to fine-tune the built-in modules or integrate their own custom recognisers and resolvers. Similarly, it is possible to include domain-specific gazetteers, allowing geoparsing workflows to be tailored to diverse research and practical contexts.

# Statement of Need

Geoparsing is an essential step in linking text to geographical locations [@purves2018], enabling diverse applications including mapping news coverage, exploring historical documents, or analysing discourse across regions [@teitler2008; @grover2010; @chesnokova2019]. Although several geoparsers already exist, they have limitations that restrict their practical applicability. Systems such as the Edinburgh Geoparser [@grover2010], CLAVIN [@berico2012], GeoTxt [@karimzadeh2019], and the Mordecai family [@halterman2017; @halterman2023] have contributed significantly to the field, but they generally require substantial effort for deployment and offer only limited flexibility in the customisation of the geoparsing process. Adapting these tools to a specific task, whether by incorporating new models for languages other than English, using specialised gazetteers or aligning the pipeline to a domain typically entails maintaining a separate fork of the software.

The Irchel Geoparser addresses these limitations by providing a clearly defined, interchangeable geoparsing pipeline packaged as an installable Python library. Its built-in modules offer strong default performance for English text and all stages of the pipeline can be adapted or exchanged entirely. This makes the Irchel Geoparser suitable both as a ready-to-use tool and as an experimental platform for researchers developing new geoparsing methods. By developing a modular architecture, we make it possible for other researchers to integrate customised modules addressing individual elements of the geoparsing workflow - for example recent work using LLMs to enhance toponym recognition [@yan2024] or resolution [@yan2024; @hu2024; @anuradha2025].

# Architecture

The Irchel Geoparser treats geoparsing as a pipeline composed of recogniser and resolver modules that adhere to simple, well-defined interfaces. Any Python class implementing these interfaces can be used within the pipeline, allowing users to integrate custom methods while relying on the system for data handling, caching, and tracking. In this structure, documents and geoparsing results are managed within a local SQLite database, enabling persistent storage for long-term workflows, by maintaining a project structure in which raw text, recognised toponyms, resolver outputs and auxiliary metadata are stored together.

The built-in recogniser uses spaCy's named-entity recognition functionality to identify toponyms based on entity labels such as Geopolitical Entity (GPE), Location (LOC), or Facility (FAC). Because it builds directly on spaCy models, users can easily switch languages, use fine-tuned models or incorporate custom pipelines by simply specifying a different model. The built-in resolver incorporates an embedding-based disambiguation method presented in prior work [@gomes2024]. It retrieves candidate locations from a gazetteer, embeds both the mention context and candidate descriptions using a transformer model, and ranks candidates based on embedding similarity. Users can choose to use the default model that has been fine-tuned using English news articles linked to GeoNames, or they can supply their own transformer checkpoints, which in turn can be trained for use with any configured gazetteer.

The gazetteer layer itself is also customisable. While a GeoNames-based configuration is provided by default, users can create gazetteer configuration files to build custom gazetteers, combining different data sources as required. This makes integrating gazetteer data created for, for example, historical georeferencing [@grossner2023] or by national mapping agencies, straightforward. Since modules only depend on the gazetteer interface, switching between different gazetteers requires no additional code changes.

# Applications

The Irchel Geoparser has been used in both research and teaching contexts. For example, it supported a study on geographic bias in global climate disaster reporting, in which thousands of news articles were analysed and mapped to reveal patterns in the geographic focus of media attention [@kong2025]. It was also used in a Master's thesis that investigated the wolf debate in Switzerland, enabling shifts in the geographic focus of the debate to be mapped over time [@besse2025]. Straightforward installation, comprehensive documentation, and a complete demo available as a Docker image also make the Irchel Geoparser an accessible tool for teaching and for illustrating key concepts in geographic information retrieval.

# Acknowledgements

The development of the Irchel Geoparser was supported by the GIS Hub, a project funded by the Digital Society Initiative (DSI) of the University of Zurich. Additional funding was provided by the Public Data Lab of the Digitalization Initiative of the Zurich Higher Education Institutions (DIZH). We thank Michele Volpi for his involvement in developing the first version of the Irchel Geoparser, and Nicolas Spring for his contributions as an open-source collaborator.

# References

